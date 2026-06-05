import React, { useState, useEffect } from 'react'
import { supabase } from './supabaseClient'

function daysLeft(deadline) {
  if (!deadline) return null
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24))
}

function urgencyColor(days) {
  if (days === null) return 'var(--muted)'
  if (days <= 7) return '#dc2626'
  if (days <= 14) return '#d97706'
  return 'var(--teal)'
}

export default function Cart({ session, bookmarks, onClose, onRemove }) {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [reminderSent, setReminderSent] = useState(false)

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
    await supabase.from('bookmarks').delete().eq('listing_id', id)
    setListings(prev => prev.filter(l => l.id !== id))
    onRemove(id)
  }
    
  const handleSendReminder = () => {
    if (listings.length === 0) return

    const lines = listings.map(l => {
      const days = daysLeft(l.deadline)
      const deadlineStr = l.deadline
        ? `Deadline: ${new Date(l.deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })} (${days >= 0 ? days + ' days left' : 'passed'})`
        : 'Deadline: Not specified'
      return `• ${l.title}\n  ${l.institution}${l.location ? ' · ' + l.location : ''}\n  ${deadlineStr}\n  ${l.link || 'No link provided'}`
    }).join('\n\n')

    const body = `Hi,\n\nHere are your saved opportunities from Alaye:\n\n${lines}\n\nVisit Alaye: https://alaye-navy.vercel.app\n\nGood luck with your applications!`
    window.open(`mailto:${session.user.email}?subject=Alaye — My Saved Opportunities&body=${encodeURIComponent(body)}`)
    setReminderSent(true)
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
        <div style={{ background: '#fef9ec', border: '0.5px solid #f0e4b8', borderRadius: 'var(--radius)', padding: '10px 14px', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ fontSize: 13 }}>
            <i className="ti ti-bell" aria-hidden="true" style={{ color: 'var(--gold)', marginRight: 6 }} />
            <strong>{listings.length}</strong> saved opportunit{listings.length > 1 ? 'ies' : 'y'} · get a deadline summary
          </div>
          <button
            onClick={handleSendReminder}
            style={{ background: 'var(--gold)', color: 'var(--ink)', border: 'none', padding: '6px 14px', borderRadius: 'var(--radius)', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' }}
          >
            {reminderSent ? '✅ Sent!' : 'Email me reminders'}
          </button>
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
                    title="Remove from cart"
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
