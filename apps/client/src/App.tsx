import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useWebSocket } from './hooks/useWebSocket';
import { StaffDashboard } from './pages/StaffDashboard';
import { AttendeeGuide } from './pages/AttendeeGuide';

const App: React.FC = () => {
  // Initialize the singleton WebSocket connection for the "stadium" venue
  useWebSocket('stadium');

  return (
    <Router>
      <div className="app-container" role="none">
        {/* Skip Navigation for Keyboard Accessibility */}
        <a href="#main-content" style={{ position: 'absolute', left: '-9999px', top: 'auto', width: '1px', height: '1px', overflow: 'hidden' }}>
          Skip to main content
        </a>
        
        <Routes>
          <Route path="/staff" element={<StaffDashboard />} />
          <Route path="/attendee" element={<AttendeeGuide />} />
          <Route path="/" element={<Navigate to="/staff" replace />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
