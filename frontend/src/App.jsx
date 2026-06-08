import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import RegisterTripPage from './pages/RegisterTripPage';
import TripHistoryPage from './pages/TripHistoryPage';
import PredictionDashboard from './pages/PredictionDashboard';
import ScheduleApprovalPage from './pages/ScheduleApprovalPage';

function PrivateRoute({ children }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
      <Route path="/trips/new" element={<PrivateRoute><RegisterTripPage /></PrivateRoute>} />
      <Route path="/trips" element={<PrivateRoute><TripHistoryPage /></PrivateRoute>} />
      <Route path="/predictions" element={<PrivateRoute><PredictionDashboard /></PrivateRoute>} />
      <Route path="/schedule" element={<PrivateRoute><ScheduleApprovalPage /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
