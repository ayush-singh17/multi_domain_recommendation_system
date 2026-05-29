import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import API from '../api/axios';

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm]       = useState({ email:'', name:'', institution:'', password:'' });
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);
  const handleChange = e => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      await API.post('/auth/register/', form);
      navigate('/login');
    } catch (err) {
      const d = err.response?.data;
      if (d?.email) setError('Email already registered.');
      else if (d?.password) setError(d.password[0]);
      else setError('Registration failed. Please try again.');
    } finally { setLoading(false); }
  };

  return (
    <div className="auth-container">
      <div className="auth-logo animate-fade-up">
        <span>◈</span> JournalFinder
      </div>
      <div className="auth-tagline animate-fade-up-1">The Digital Curator for Modern Research</div>

      <div className="auth-box animate-fade-up-2">
        <div className="auth-tabs">
          <button className="auth-tab" onClick={() => navigate('/login')}>Sign In</button>
          <button className="auth-tab active">Sign Up</button>
        </div>

        <h1 className="auth-heading">Create Account</h1>
        <p className="auth-sub">Join thousands of researchers using AI-powered journal discovery.</p>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input className="form-input" name="name" value={form.name} onChange={handleChange} placeholder="Dr. Jane Smith" required />
          </div>
          <div className="form-group">
            <label className="form-label">Academic Email</label>
            <input className="form-input" name="email" type="email" value={form.email} onChange={handleChange} placeholder="dr.smith@university.edu" required />
          </div>
          <div className="form-group">
            <label className="form-label">Institution <span style={{color:'var(--text-3)',fontWeight:400,textTransform:'none',letterSpacing:0}}>(optional)</span></label>
            <input className="form-input" name="institution" value={form.institution} onChange={handleChange} placeholder="MIT, Stanford, Oxford..." />
          </div>
          <div className="form-group">
            <label className="form-label">Access Key</label>
            <input className="form-input" name="password" type="password" value={form.password} onChange={handleChange} placeholder="Min. 8 characters" required />
          </div>
          <button className="btn-init" type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Initialize Account'}
          </button>
        </form>
        <p className="auth-footer" style={{marginTop:'1rem'}}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
