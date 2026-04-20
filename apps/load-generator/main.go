package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

// Metrics tracks the test performance using atomic counters for concurrency safety
type Metrics struct {
	RestSuccess      atomic.Uint64
	RestFail         atomic.Uint64
	WsMessages       atomic.Uint64
	LatencyMu        sync.Mutex
	RoutingLatencies []float64
}

var metrics Metrics

type RouteRequest struct {
	StartID int `json:"start_id"`
	GoalID  int `json:"goal_id"`
}

func main() {
	targetWorkers := flag.Int("workers", 1000, "Total number of concurrent workers")
	rampUpRate := flag.Int("ramp", 50, "Workers to launch per second")
	baseURL := flag.String("url", "http://localhost:8000", "Base URL of the FastAPI server")
	wsURL := flag.String("ws", "ws://localhost:8000", "Base WebSocket URL")
	duration := flag.Int("duration", 30, "Duration of the test in seconds")
	flag.Parse()

	log.Printf("Starting Load Test: %d workers, %d/sec ramp-up", *targetWorkers, *rampUpRate)

	var wg sync.WaitGroup
	ctx := time.After(time.Duration(*duration) * time.Second)
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	currentWorkers := 0
	
	// Orchestrator: Linear Ramp-up
	for currentWorkers < *targetWorkers {
		select {
		case <-ticker.C:
			toLaunch := *rampUpRate
			if currentWorkers+toLaunch > *targetWorkers {
				toLaunch = *targetWorkers - currentWorkers
			}
			for i := 0; i < toLaunch; i++ {
				wg.Add(1)
				go worker(currentWorkers+i, *baseURL, *wsURL, &wg, ctx)
			}
			currentWorkers += toLaunch
			log.Printf("Launched %d/%d workers...", currentWorkers, *targetWorkers)
		}
	}

	wg.Wait()
	printReport()
}

func worker(id int, baseURL, wsURL string, wg *sync.WaitGroup, ctx <-chan time.Time) {
	defer wg.Done()

	// 1. Dial WebSocket
	url := fmt.Sprintf("%s/ws/venue/stadium", wsURL)
	conn, _, err := websocket.DefaultDialer.Dial(url, nil)
	if err != nil {
		log.Printf("Worker %d: WS Dial failed: %v", id, err)
		return
	}
	defer conn.Close()

	// 2. Background WS Listener
	go func() {
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				return
			}
			// Parse minified JSON: {"z": 14, "w": 5.2}
			var update map[string]interface{}
			if err := json.Unmarshal(message, &update); err == nil {
				metrics.WsMessages.Add(1)
			}
		}
	}()

	// 3. Behavioral REST Loop
	client := &http.Client{Timeout: 2 * time.Second}
	
	for {
		select {
		case <-ctx:
			return
		default:
			// Random behavior: Sleep 1-5 seconds
			time.Sleep(time.Duration(1+rand.Intn(4)) * time.Second)
			
			// a. POST /api/v1/route (High Frequency)
			sendRouteRequest(client, baseURL)
			
			// b. POST /api/v1/concierge (Lower Frequency)
			if rand.Float32() < 0.1 {
				sendConciergeRequest(client, baseURL)
			}
		}
	}
}

func sendRouteRequest(client *http.Client, baseURL string) {
	start := time.Now()
	
	// Random node IDs from test.venue (0 to 3)
	reqBody, _ := json.Marshal(RouteRequest{
		StartID: rand.Intn(4),
		GoalID:  rand.Intn(4),
	})
	
	resp, err := client.Post(baseURL+"/api/v1/route", "application/json", bytes.NewBuffer(reqBody))
	latency := time.Since(start).Seconds() * 1000

	if err != nil || resp.StatusCode != 200 {
		metrics.RestFail.Add(1)
		return
	}
	defer resp.Body.Close()
	
	metrics.RestSuccess.Add(1)
	
	// Track Latency (Locked context for slice safety)
	metrics.LatencyMu.Lock()
	metrics.RoutingLatencies = append(metrics.RoutingLatencies, latency)
	metrics.LatencyMu.Unlock()
}

func sendConciergeRequest(client *http.Client, baseURL string) {
	reqBody, _ := json.Marshal(map[string]string{
		"prompt": "How do I get to MainArena?",
		"role":   "attendee",
	})
	resp, err := client.Post(baseURL+"/api/v1/concierge", "application/json", bytes.NewBuffer(reqBody))
	if err == nil && resp.StatusCode == 200 {
		resp.Body.Close()
	}
}

func printReport() {
	fmt.Println("\n--- Load Test Report ---")
	fmt.Printf("REST Success: %d\n", metrics.RestSuccess.Load())
	fmt.Printf("REST Failure: %d\n", metrics.RestFail.Load())
	fmt.Printf("WS Messages Received: %d\n", metrics.WsMessages.Load())

	sort.Float64s(metrics.RoutingLatencies)
	if len(metrics.RoutingLatencies) > 0 {
		p95 := metrics.RoutingLatencies[int(float64(len(metrics.RoutingLatencies))*0.95)]
		p99 := metrics.RoutingLatencies[int(float64(len(metrics.RoutingLatencies))*0.99)]
		fmt.Printf("Routing Latency (P95): %.2f ms\n", p95)
		fmt.Printf("Routing Latency (P99): %.2f ms\n", p99)
	}
}
