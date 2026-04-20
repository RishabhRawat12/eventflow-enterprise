import React, { useState, useRef, useEffect } from 'react';
import { useVenueStore } from '../store/useStore';
import { Map } from '../components/Map';
import { MessageSquare, Navigation, Map as MapIcon } from 'lucide-react';

export const AttendeeGuide: React.FC = () => {
  const { attendeeMessages, addAttendeeMessage } = useVenueStore();
  const [input, setInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [attendeeMessages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userPrompt = input;
    setInput('');
    
    // Simulate API call to /api/v1/concierge
    try {
      const response = await fetch('/api/v1/concierge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userPrompt, role: 'attendee' }),
      });
      const data = await response.json();
      addAttendeeMessage(data);
    } catch (err) {
      addAttendeeMessage({ answer: "Sorry, I'm having trouble connecting to the concierge right now." });
    }
  };

  return (
    <div className="attendee-guide app-container">
      <header role="banner" style={{ textAlign: 'center', padding: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.25rem' }}>Stadium Assistant</h1>
      </header>

      <main style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: 0 }}>
        {/* Navigation Map */}
        <section aria-labelledby="map-label">
          <h2 id="map-label" style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <MapIcon size={18} />
            Live Navigation
          </h2>
          <div style={{ height: '300px', width: '100%' }}>
            <Map />
          </div>
        </section>

        {/* AI Concierge Chat */}
        <section aria-labelledby="chat-label" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem', background: 'var(--bg-secondary)', borderRadius: '12px', padding: '1rem' }}>
          <h2 id="chat-label" style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
            <MessageSquare size={18} />
            AI Concierge
          </h2>

          <div style={{ flex: 1, overflowY: 'auto', minHeight: '200px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }} role="log" aria-live="polite">
            {attendeeMessages.length === 0 && (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '2rem' }}>
                Ask me for directions or the best time to visit the arena!
              </p>
            )}
            {attendeeMessages.map((msg, i) => (
              <div key={i} style={{ background: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--accent-secondary)' }}>
                <p style={{ margin: 0 }}>{msg.answer}</p>
                {msg.itinerary && (
                  <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                    <strong>Plan:</strong>
                    {msg.itinerary.map((step, si) => (
                      <div key={si}>{step.time}: {step.action}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={handleSend} style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the concierge..."
              placeholder-aria-label="Chat input"
              style={{ flex: 1, padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--text-secondary)', background: 'var(--bg-primary)', color: 'white' }}
              aria-label="Message to concierge"
            />
            <button 
              type="submit" 
              style={{ background: 'var(--accent-primary)', color: 'black', border: 'none', padding: '0 1rem', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}
              aria-label="Send message"
            >
              Send
            </button>
          </form>
        </section>
      </main>

      <nav role="navigation" style={{ padding: '0.75rem', display: 'flex', justifyContent: 'space-around', borderTop: '1px solid var(--bg-secondary)', marginTop: 'auto' }}>
        <button style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem' }}>
          <Navigation size={20} />
          <span style={{ fontSize: '0.7rem' }}>Navigation</span>
        </button>
      </nav>
    </div>
  );
};
