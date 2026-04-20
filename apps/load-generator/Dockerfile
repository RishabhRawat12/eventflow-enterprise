# Build Stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy dependency files
COPY go.mod ./
# Note: go.sum will be generated on go mod download if not present
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -o load-gen .

# Final Stage
FROM alpine:latest

WORKDIR /app
COPY --from=builder /app/load-gen .

# Environment variables for the server location
ENV SERVER_URL=http://host.docker.internal:8000
ENV WS_URL=ws://host.docker.internal:8000

# Default execution: 1000 workers for 30 seconds
ENTRYPOINT ["./load-gen", "-url", "http://host.docker.internal:8000", "-ws", "ws://host.docker.internal:8000"]
