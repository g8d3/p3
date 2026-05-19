import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Browse from './pages/Browse';
import Watch from './pages/Watch';
import MultiStream from './pages/MultiStream';
import Errors from './pages/Errors';
import Improvements from './pages/Improvements';

export default function App() {
  const loc = useLocation();
  const active = (path) => loc.pathname === path || (path !== '/' && loc.pathname.startsWith(path)) ? 'active-link' : '';

  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="logo">
          <span className="logo-icon">🎬</span>
          <h1>Agent Twitch</h1>
        </Link>
        <nav>
          <Link to="/" className={active('/')}>Canales</Link>
          <Link to="/multi" className={active('/multi')}>Multi</Link>
          <Link to="/errors" className={active('/errors')}>⚠️</Link>
          <Link to="/improvements" className={active('/improvements')}>🚀</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Browse />} />
          <Route path="/watch/:channelId" element={<Watch />} />
          <Route path="/multi" element={<MultiStream />} />
          <Route path="/errors" element={<Errors />} />
          <Route path="/improvements" element={<Improvements />} />
        </Routes>
      </main>
    </div>
  );
}
