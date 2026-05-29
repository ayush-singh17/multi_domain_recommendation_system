import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import API from '../api/axios';

// ─────────────────────────────────────────────────────────────────────────────
// Google OAuth — uses Google Identity Services (GSI) popup flow
// Apple OAuth  — uses Apple JS SDK popup flow
//
// SETUP REQUIRED (see bottom of this file for instructions):
//   Google: set REACT_APP_GOOGLE_CLIENT_ID in your .env
//   Apple:  set REACT_APP_APPLE_CLIENT_ID + REACT_APP_APPLE_REDIRECT_URI in .env
// ─────────────────────────────────────────────────────────────────────────────

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

export default function Login() {
  const { login, setUserFromToken } = useAuth();
  const navigate                    = useNavigate();

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [socialLoading, setSocialLoading] = useState(''); // 'google' | 'apple' | ''

  // ── Load Google GSI script once ──────────────────────────────────────────
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const script = document.createElement('script');
    script.src   = 'https://accounts.google.com/gsi/client';
    script.async = true;
    document.body.appendChild(script);
    return () => document.body.removeChild(script);
  }, []);

  // ── Email/password login ─────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch {
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // ── Google login ─────────────────────────────────────────────────────────
  const handleGoogle = () => {
    if (!GOOGLE_CLIENT_ID) {
      setError('Google login is not configured yet.');
      return;
    }

    if (!window.google) {
      setError('Google script not loaded yet. Please wait a moment and try again.');
      return;
    }

    setSocialLoading('google');
    setError('');

    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: GOOGLE_CLIENT_ID,
      scope: 'openid email profile',
      callback: '', // will be set below
    });

    // Use the ID token flow instead
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        try {
          // 1. Send id_token to Django
          const res = await API.post('/auth/social/google/', {
            id_token: response.credential,
          });

          // 2. Save tokens
          localStorage.setItem('access_token',  res.data.access);
          localStorage.setItem('refresh_token', res.data.refresh);

          // 3. Fetch profile
          const profile = await API.get('/auth/profile/');

          // 4. Set user and navigate
          setUserFromToken(profile.data);
          navigate('/');
        } catch (err) {
          console.error('Google login error:', err?.response?.data || err.message);
          setError('Google login failed: ' + (err?.response?.data?.error || 'Please try again.'));
          setSocialLoading('');
        }
      },
    });

    // Open the Google One Tap / popup
    window.google.accounts.id.prompt((notification) => {
      // One Tap was suppressed or skipped — fall back to renderButton click
      if (
        notification.isNotDisplayed() ||
        notification.isSkippedMoment() ||
        notification.isDismissedMoment()
      ) {
        // Render a hidden button and click it to force the popup
        const container = document.getElementById('google-btn-hidden');
        if (container) {
          container.innerHTML = ''; // clear previous render
          window.google.accounts.id.renderButton(container, {
            type: 'standard',
            theme: 'outline',
            size: 'large',
          });
          const btn = container.querySelector('div[role=button]') || container.querySelector('iframe');
          if (btn) btn.click();
        }
        setSocialLoading('');
      }
    });
  };

  return (
    <div className="auth-container">

      {/* Logo */}
      <div className="auth-logo animate-fade-up">
        <span className="auth-logo-icon">📖</span> JournalFinder
      </div>
      <div className="auth-tagline animate-fade-up-1">The Digital Curator for Modern Research</div>

      {/* Card */}
      <div className="auth-box animate-fade-up-2">

        {/* Tabs */}
        <div className="auth-tabs">
          <button className="auth-tab active">Sign In</button>
          <button className="auth-tab" onClick={() => navigate('/register')}>Sign Up</button>
        </div>

        <h1 className="auth-heading">Welcome Back</h1>
        <p className="auth-sub">Access your curated academic intelligence engine.</p>

        {error && <div className="error-msg">{error}</div>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Academic Email</label>
            <input
              className="form-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="dr.smith@university.edu"
              required
            />
          </div>

          <div className="form-group">
            <div className="form-label-row">
              <label className="form-label">Access Key</label>
              <span className="form-label-link">Forgot?</span>
            </div>
            <input
              className="form-input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
          </div>

          <div className="auth-secure">
            <label style={{display:'flex',alignItems:'center',gap:'.5rem',fontSize:'.73rem',color:'var(--text-3)',cursor:'pointer'}}>
              <input type="checkbox" style={{accentColor:'var(--indigo)'}} />
              Trust this device
            </label>
            <div className="secure-badge">
              <div className="secure-dot" />
              Secure Link Active
            </div>
          </div>

          <button className="btn-init" type="submit" disabled={loading || !!socialLoading}>
            {loading ? 'Initializing...' : 'Initialize Session'}
          </button>
        </form>

        {/* Divider */}
        <div className="auth-divider">or continue with</div>

        {/* Social buttons */}
        <div className="federated-btns">
          <button
            className="btn-federated"
            onClick={handleGoogle}
            disabled={!!socialLoading}
          >
            {socialLoading === 'google' ? (
              <span className="social-spinner" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
                <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
              </svg>
            )}
            Continue with Google
          </button>
        </div>

        <p className="auth-footer">
          Don't have an account?{' '}
          <Link to="/register">Create one</Link>
        </p>
      </div>

      {/* Stats */}
      <div className="auth-stats animate-fade-up-3">
        <div className="auth-stat">
          <div className="num">29,553</div>
          <div className="lbl">Journals Indexed</div>
        </div>
        <div className="auth-stat">
          <div className="num">BERT</div>
          <div className="lbl">Semantic Engine</div>
        </div>
        <div className="auth-stat">
          <div className="num">3-Tier</div>
          <div className="lbl">Strategy Plans</div>
        </div>
      </div>

      {/* Hidden div needed for Google button fallback */}
      <div id="google-btn-hidden" style={{display:'none'}} />
    </div>
  );
}

/*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GOOGLE OAUTH SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to https://console.cloud.google.com
2. Create a project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID → Web application
4. Add http://localhost:3000 to Authorized JS origins
5. Copy the Client ID and add to your frontend .env:
     REACT_APP_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

6. Add to Django (pip install google-auth):
   In users/views.py:

     from google.oauth2 import id_token
     from google.auth.transport import requests as google_requests
     from rest_framework.views import APIView
     from rest_framework.permissions import AllowAny
     from rest_framework.response import Response
     from rest_framework_simplejwt.tokens import RefreshToken

     GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

     class GoogleLoginView(APIView):
         permission_classes = [AllowAny]
         def post(self, request):
             token = request.data.get('id_token')
             info  = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
             email = info['email']
             name  = info.get('name', email.split('@')[0])
             user, _ = User.objects.get_or_create(email=email, defaults={'name': name})
             refresh = RefreshToken.for_user(user)
             return Response({'access': str(refresh.access_token), 'refresh': str(refresh)})

7. Add to users/urls.py:
     path('social/google/', GoogleLoginView.as_view()),

8. Add GOOGLE_CLIENT_ID to your backend .env too:
     GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*/
