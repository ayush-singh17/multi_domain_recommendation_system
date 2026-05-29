import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location         = useLocation();
  const initials         = user?.name?.split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase() || 'U';

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand" style={{textDecoration:'none'}}>JournalFinder</Link>
      <div className="navbar-links">
        <Link to="/"        className={'nav-link' + (location.pathname === '/'        ? ' active' : '')}>Search</Link>
        <Link to="/history" className={'nav-link' + (location.pathname === '/history' ? ' active' : '')}>History</Link>
      </div>
      <div className="navbar-user">
        <span className="user-name">{user?.name}</span>
        <div className="user-avatar" title={user?.email}>{initials}</div>
        <button className="btn-logout" onClick={logout}>Sign Out</button>
      </div>
    </nav>
  );
}
