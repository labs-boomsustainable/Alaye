import React, { useState } from 'react'
import { supabase } from './supabaseClient'

export default function Auth({ onClose }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState(null)

  const handleLogin = async () => {
    if (!email.trim()) { setError('Please enter your email'); return }
    setLoading(true)
    setError(null)
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: window.location.origin,
      }
    })
    setLoading(false)
    if (error) { setError(error.message); return }
    setSent(true)
  }

  return (
    <div className="modal">
      {!sent ? (
        <>
          <div className="modal-hdr">
            <div className="modal-title">Sign in to Alaye</div>
            <button className="btn-close" onClick={onClose}>
              <i className="ti ti-x" aria-hidden="true" />
            </button>
          </div>
          <p style={{ fontSize: 14, color: 'var(--muted)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
            Enter your email and we'll send you a magic link — no password needed.
          </p>
          <div className="form-group">
            <label className="form-label">Email address</label>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
              autoFocus
            />
          </div>
          {error && (
            <div style={{ fontSize: 13, color: '#7f1d1d', background: '#fee2e2', padding: '8px 12px', borderRadius: 8, marginBottom: 12 }}>
              {error}
            </div>
          )}
          <button className="btn-submit" onClick={handleLogin} disabled={loading}>
            {loading ? 'Sending…' : 'Send magic link →'}
          </button>
          <p style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', marginTop: 16 }}>
            No account needed — signing in creates your account automatically.
          </p>
        </>
      ) : (
        <div className="success">
          <i className="ti ti-mail-forward" aria-hidden="true" style={{ fontSize: 44, color: 'var(--teal)', display: 'block', marginBottom: '1rem' }} />
          <div style={{ fontFamily: 'Lora, serif', fontSize: 18, fontWeight: 500 }}>Check your inbox</div>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8, lineHeight: 1.6 }}>
            We sent a magic link to <strong>{email}</strong>.<br />
            Click it to sign in — it expires in 1 hour.
          </p>
          <button className="btn-primary" style={{ marginTop: '1.5rem' }} onClick={onClose}>
            Close
          </button>
        </div>
      )}
    </div>
  )
}
