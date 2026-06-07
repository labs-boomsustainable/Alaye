import React, { useState, useEffect } from 'react'
import { supabase } from './supabaseClient'

function daysLeft(deadline) {
  if (!deadline) return null
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24))
}

function urgencyColor(days) {
  if (days === null) return 'var(--muted)'
  if (days <= 5) return '#dc2626'
  if (days <= 14) return '#d97706'
  return 'var(--teal)'
}

export default function Cart({ userEmail, session, bookmarks, onClose, onRemove }) {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)
  const [error, setError] = useState(null)
  const [cartEmail, setCartEmail] = useState('')

  const emailToUse = userEmail || session?.user?.email

  useEffect(() => {
    if (bookmarks.size === 0) { setListings([]); setLoading(false); return }
    const ids = [...bookmarks]
    supabase
      .from('listings')
      .select('*')
      .in('id', ids)
      .then(({ data }) => {
        if (data) {
          const sorted = data.sort((a, b) => {
            if (!a.deadline) return 1
            if (!b.deadline) return -1
            return new Date(a.deadline) - new Date(b.deadline)
          })
          setListings(sorted)
        }
        setLoading(false)
      })
  }, [bookmarks])

  const handleRemove = async (id) => {
    if (emailToUse) {
      await supabase.from('subscribers').delete().eq('listing_id', id).eq('email', emailToUse)
    }
    setListings(prev => prev.filter(l => l.id !== id))
    onRemove(id)
  }
  
  const handleSaveEmail = async () => {
    const email = cartEmail.trim().toLowerCase()
    if (!email || !email.includes('@')) return
    localStorage.setItem('alaye_email', email)
    for (const l of listings) {
      await supabase.from('subscribers').upsert([{ email, listing_id: l.id }])
    }
    window.location.reload()
  }

  const handleSendEmail = async () => {
    if (!emailToUse || listings.length === 0) return
    setSending(true)
    setError(null)

    const urgent = listings.filter(l => { const d = daysLeft(l.deadline); return d !== null && d >= 0 && d <= 5 })
    const upcoming = listings.filter(l => { const d = daysLeft(l.deadline); return d !== null && d > 5 && d <= 30 })
    const rest = listings.filter(l => { const d = daysLeft(l.deadline); return d === null || d > 30 || d < 0 })

    const typeLabels = { phd: 'PhD', msc: 'MSc', postdoc: 'Postdoc', paper: 'Paper Call', grant: 'Grant', conf: 'Conference' }

    const cardHtml = (l) => {
      const d = daysLeft(l.deadline)
      const deadlineColor = d !== null && d <= 5 ? '#dc2626' : d !== null && d <= 14 ? '#d97706' : '#0f6e56'
      const deadlineStr = l.deadline
        ? d >= 0 ? `${d} days left — ${new Date(l.deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}` : 'Deadline passed'
        : 'No deadline specified'
      return `
        <div style="background:#ffffff;border:1px solid #e8e0d4;border-radius:10px;padding:18px 20px;margin-bottom:12px;">
          <span style="background:#f0e4b8;color:#7a5800;font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;">${typeLabels[l.type] || 'Opportunity'}</span>
          <div style="font-family:Georgia,serif;font-size:16px;font-weight:600;color:#1a1612;margin:10px 0 4px;">${l.title}</div>
          <div style="font-size:13px;color:#6b6358;margin-bottom:6px;">${l.institution}${l.location ? ' · ' + l.location : ''}</div>
          ${l.field ? `<div style="font-size:13px;color:#6b6358;margin-bottom:4px;">📚 ${l.field}</div>` : ''}
          ${l.funding ? `<div style="font-size:13px;color:#6b6358;margin-bottom:8px;">💰 ${l.funding}</div>` : ''}
          <div style="font-size:13px;font-weight:600;color:${deadlineColor};margin-bottom:${l.description ? '8px' : '12px'};">⏰ ${deadlineStr}</div>
          ${l.description ? `<div style="font-size:13px;color:#555;line-height:1.6;margin-bottom:12px;">${l.description}</div>` : ''}
          ${l.link ? `<a href="${l.link}" style="background:#0f6e56;color:#ffffff;text-decoration:none;padding:8px 18px;border-radius:8px;font-size:13px;font-weight:500;">View & Apply →</a>` : ''}
        </div>`
    }

    const urgentSection = urgent.length > 0 ? `
      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px 18px;margin-bottom:16px;">
        <div style="font-size:14px;font-weight:600;color:#dc2626;">🚨 Act now — deadline in 5 days or less</div>
        <div style="font-size:13px;color:#7f1d1d;margin-top:4px;">These opportunities are closing very soon.</div>
      </div>
      ${urgent.map(cardHtml).join('')}
      ${upcoming.length > 0 ? '<div style="font-family:Georgia,serif;font-size:15px;font-weight:600;color:#1a1612;margin:20px 0 12px;">📅 Coming up in the next 30 days</div>' : ''}
    ` : ''

    const upcomingSection = upcoming.map(cardHtml).join('')
    const restSection = rest.length > 0 ? `
      <div style="font-family:Georgia,serif;font-size:15px;font-weight:600;color:#1a1612;margin:20px 0 12px;">📌 Your other saved opportunities</div>
      ${rest.map(cardHtml).join('')}
    ` : ''

    const html = `
      <!DOCTYPE html>
      <html>
      <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
      <body style="margin:0;padding:0;background:#f2ede6;font-family:Arial,sans-serif;">
        <div style="max-width:600px;margin:0 auto;padding:32px 16px;">
          <div style="background:#1a1612;border-radius:12px 12px 0 0;padding:28px;">
            <div style="font-family:Georgia,serif;font-size:26px;font-weight:700;color:#f7f3ec;">Alaye<span style="color:#b8860b;">.</span></div>
            <div style="font-size:11px;color:rgba(247,243,236,0.5);letter-spacing:0.8px;text-transform:uppercase;margin-top:3px;">Open Academic Opportunities</div>
          </div>
          <div style="background:#ffffff;padding:28px;border-radius:0 0 12px 12px;margin-bottom:20px;">
            <div style="font-family:Georgia,serif;font-size:20px;font-weight:600;color:#1a1612;margin-bottom:8px;">Your saved opportunities</div>
            <div style="font-size:14px;color:#6b6358;line-height:1.7;margin-bottom:24px;">
              Here is a summary of your <strong>${listings.length}</strong> saved opportunit${listings.length !== 1 ? 'ies' : 'y'} on Alaye.
              ${urgent.length > 0 ? `<strong style="color:#dc2626;"> You have ${urgent.length} closing in 5 days — act fast!</strong>` : ' Stay on top of your applications and good luck!'}
            </div>
            ${urgentSection}
            ${upcomingSection}
            ${restSection}
            <div style="margin-top:28px;padding-top:20px;border-top:1px solid #e8e0d4;text-align:center;">
              <a href="https://alaye-agent.live" style="background:#b8860b;color:#1a1612;text-decoration:none;padding:12px 28px;border-radius:10px;font-size:14px;font-weight:600;">Browse more opportunities →</a>
            </div>
          </div>
          <div style="text-align:center;font-size:11px;color:#aaa;padding:0 0 24px;">
            You are receiving this because you saved opportunities on Alaye.<br>
            Visit <a href="https://alaye-agent.live" style="color:#0f6e56;">alaye-agent.live</a> to manage your saved items.
          </div>
        </div>
      </body>
      </html>`

    try {
      const response = await fetch(
        `${process.env.REACT_APP_SUPABASE_URL}/functions/v1/email-reminder`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.REACT_APP_SUPABASE_ANON_KEY}`
          },
          body: JSON.stringify({
            to: emailToUse,
            subject: `Alaye — Your ${listings.length} saved opportunit${listings.length !== 1 ? 'ies' : 'y'}${urgent.length > 0 ? ' 🚨 ' + urgent.length + ' closing soon!' : ''}`,
            html
          })
        }
      )
      const data = await response.json()
      if (response.ok && data.success) {
        setEmailSent(true)
        setTimeout(() => setEmailSent(false), 5000)
      } else {
        setError(data.error || 'Failed to send email. Try again.')
      }
    } catch (e) {
      setError('Network error. Please try again.')
    }
    setSending(false)
  }

  return (
    <div className="modal" style={{ maxWidth: 560 }}>
      <div className="modal-hdr">
        <div className="modal-title">
          <i className="ti ti-bookmark" aria-hidden="true" style={{ marginRight: 8 }} />
          My saved opportunities
          {listings.length > 0 && (
            <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--muted)', marginLeft: 8 }}>
              {listings.length} saved
            </span>
          )}
        </div>
        <button className="btn-close" onClick={onClose}>
          <i className="ti ti-x" aria-hidden="true" />
        </button>
      </div>

      {listings.length > 0 && (
        <div style={{ background: '#fef9ec', border: '0.5px solid #f0e4b8', borderRadius: 'var(--radius)', padding: '10px 14px', marginBottom: '1.25rem' }}>
          {emailToUse ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ fontSize: 13 }}>
                <i className="ti ti-bell" aria-hidden="true" style={{ color: 'var(--gold)', marginRight: 6 }} />
                Sending to <strong>{emailToUse}</strong>
              </div>
              <button
                onClick={handleSendEmail}
                disabled={sending || emailSent}
                style={{ background: emailSent ? 'var(--teal)' : 'var(--gold)', color: emailSent ? '#fff' : 'var(--ink)', border: 'none', padding: '6px 14px', borderRadius: 'var(--radius)', fontSize: 12, fontWeight: 500, cursor: sending ? 'wait' : 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' }}
              >
                {sending ? 'Sending…' : emailSent ? '✅ Sent!' : 'Email me reminders'}
              </button>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <i className="ti ti-bell" aria-hidden="true" style={{ color: 'var(--gold)', marginRight: 6 }} />
                Enter your email to get deadline reminders
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={cartEmail}
                  onChange={e => setCartEmail(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSaveEmail()}
                  style={{ flex: 1, padding: '7px 11px', border: '0.5px solid var(--border)', borderRadius: 'var(--radius)', fontFamily: 'inherit', fontSize: 13 }}
                />
                <button
                  onClick={handleSaveEmail}
                  style={{ background: 'var(--gold)', color: 'var(--ink)', border: 'none', padding: '7px 14px', borderRadius: 'var(--radius)', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' }}
                >
                  Save & remind me
                </button>
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>No spam. Only deadline reminders.</div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div style={{ fontSize: 13, color: '#7f1d1d', background: '#fee2e2', padding: '8px 12px', borderRadius: 8, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading your saved opportunities…</div>
      ) : listings.length === 0 ? (
        <div className="empty" style={{ padding: '2rem 1rem' }}>
          <i className="ti ti-bookmark-off" aria-hidden="true" />
          <div style={{ marginBottom: 8 }}>No saved opportunities yet</div>
          <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
            Click the bookmark icon on any listing to save it here.
          </p>
          <button onClick={onClose} style={{ marginTop: 16, background: 'none', border: 'none', color: 'var(--teal)', cursor: 'pointer', fontFamily: 'inherit', fontSize: 14, textDecoration: 'underline' }}>
            Browse opportunities
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {listings.map(l => {
            const days = daysLeft(l.deadline)
            const color = urgencyColor(days)
            return (
              <div key={l.id} style={{ background: '#f9f9f7', border: '0.5px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: 'Lora, serif', fontSize: 14, fontWeight: 500, lineHeight: 1.4, marginBottom: 4, color: 'var(--ink)' }}>
                      {l.title}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 6 }}>
                      {l.institution}{l.location && ` · ${l.location}`}
                    </div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {l.deadline && (
                        <span style={{ fontSize: 12, color, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 3 }}>
                          <i className="ti ti-calendar" aria-hidden="true" style={{ fontSize: 13 }} />
                          {days !== null && days >= 0 ? `${days} days left` : 'Deadline passed'}
                          {' '}· {new Date(l.deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                        </span>
                      )}
                      {l.funding && (
                        <span style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 3 }}>
                          <i className="ti ti-coin" aria-hidden="true" style={{ fontSize: 13 }} />
                          {l.funding}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(l.id)}
                    style={{ background: 'none', border: '0.5px solid var(--border)', borderRadius: 'var(--radius)', padding: '4px 8px', cursor: 'pointer', fontSize: 12, color: 'var(--muted)', flexShrink: 0 }}
                    title="Remove from saved"
                  >
                    <i className="ti ti-x" aria-hidden="true" />
                  </button>
                </div>
                {l.link && (
                  <div style={{ marginTop: 10, paddingTop: 8, borderTop: '0.5px solid var(--border)' }}>
                    <a href={l.link} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: 'var(--teal)', fontWeight: 500, textDecoration: 'none' }}>
                      View & apply <i className="ti ti-arrow-up-right" aria-hidden="true" style={{ fontSize: 12 }} />
                    </a>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {listings.length > 0 && (
        <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '0.5px solid var(--border)', fontSize: 12, color: 'var(--muted)', textAlign: 'center' }}>
          Sorted by deadline — closest first
        </div>
      )}
    </div>
  )
}
