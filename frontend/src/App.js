import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login    from './pages/Login';
import Register from './pages/Register';
import Search   from './pages/Search';
import Results  from './pages/Results';
import History  from './pages/History';
import Navbar   from './components/Navbar';
import RoamingBot from './components/RoamingBot';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Loading...</div>;
  return user ? children : <Navigate to="/login" />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={
          <PrivateRoute>
            <Navbar />
            <Search />
            <RoamingBot />
          </PrivateRoute>
        } />
        <Route path="/results" element={
          <PrivateRoute>
            <Navbar />
            <Results />
            <RoamingBot />
          </PrivateRoute>
        } />
        <Route path="/history" element={
          <PrivateRoute>
            <Navbar />
            <History />
            <RoamingBot />
          </PrivateRoute>
        } />
      </Routes>
    </BrowserRouter>
  );
}
