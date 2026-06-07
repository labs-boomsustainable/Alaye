import React, { useState, useEffect, useCallback } from 'react'
import { supabase } from './supabaseClient'

export default function Admin({ onClose }) {
  const [stats, setStats] = useState(null)
  const [listings, setListings] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [filter, setFilter] = useState('all')
  const [triggering, setTriggering] = useState(false)
  const [triggerResult, setTriggerResult] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const fetchData = useCallback(async () => {
    setLoading(true)

    const { data: allListings } = await supabase
      .from('listings')
      .select('*')
      .order('created_at', { ascending: false })

    const { count: userCount } = await supabase
      .from('profiles')
      .select('*', { count: 'exact', head: true })

    const { data: profileData } = await supabase
      .from('profiles')
      .select('email, role, created_at')
      .order('created_at', { ascending: false })

    if (allListings) {
      const total = allListings.length
      const agentPosts = allListings.filter(l => l.source === 'agent').length
      const communityPosts = allListings.filter(l => l.source === 'community').length
      const unverified = allListings.filter(l => !l.verified).length
      const byType = allListings.reduce((acc, l) => {
        acc[l.type] = (acc[l.type] || 0) + 1
        return acc
      }, {})

      setStats({ total, agentPosts, communityPosts, unverified, byType, userCount: userCount || 0 })
      setListings(allListings)
    }

    if (profileData) setUsers(profileData)
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const filteredListings = listings.filter(l => {
    if (filter === 'unverified') return !l.verified
    if (filter === 'agent') return l.source === 'agent'
    if (filter === 'community') return l.source === 'community'
    return true
  })

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === filteredListings.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filteredListings.map(l => l.id)))
    }
  }

  const handleBulkDelete = async () => {
    if (selected.size === 0) return
    if (!window.confirm(`Delete ${selected.size} listing${selected.size > 1 ? 's' : ''}?`)) return
    const ids = [...selected]
    const { error } = await supabase.from('listings').delete().in('id', ids)
    if (!error) {
      showToast(`${ids.length} listing${ids.length > 1 ? 's' : ''} deleted`)
      setSelected(new Set())
      fetchData()
    } else {
      showToast('Error deleting listings')
    }
  }

  const handleVerifyAll = async () => {
    if (selected.size === 0) return
    const ids = [...selected]
    const { error } = await supabase.from('listings').update({ verified: true }).in('id', ids)
    if (!error) {
      showToast(`${ids.length} listing${ids.length > 1 ? 's' : ''} verified`)
      setSelected(new Set())
      fetchData()
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this listing?')) return
    const { error } = await supabase.from('listings').delete().eq('id', id)
    if (!error) { showToast('Deleted'); fetchData() }
  }

  const handleVerify = async (id, current) => {
    const { error } = await supabase.from('listings').update({ verified: !current }).eq('id', id)
    if (!error) { showToast(current ? 'Unverified' : 'Verified!'); fetchData() }
  }

  const handleTriggerAgent = async () => {
    setTriggering(true)
    setTriggerResult(null)
    try {
      const response = await fetch(
        'https://api.github.com/repos/labs-boomsustainable/Alaye/actions/workflows/agent.yml/dispatches',
        {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ref: 'main', inputs: { job: 'agent' } })
        }
      )
      if (response.status === 204) {
        setTriggerResult('✅ Agent triggered! Check GitHub Actions for progress.')
      } else {
        setTriggerResult('⚠️ Could not trigger agent. Run manually from GitHub Actions.')
      }
    } catch (e) {
      setTriggerResult('⚠️ Could not trigger agent. Run manually from GitHub Actions.')
    }
    setTriggering(false)
  }

  const typeLabels = { phd: 'PhD', msc: 'MSc', postdoc: 'Postdoc', paper: 'Paper', grant: 'Grant', conf: 'Conference' }

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#f2ede6', zIndex: 300, overflowY: 'auto' }}>
      <div style={{ maxWidth: 900px, margin: '0 auto', padding: '2rem 1rem 5rem' }}>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
          <div>
            <div style={{ fontFamily: 'Lora, serif', fontSize: 24, fontWeight: 600, color: 'var(--ink)' }}>
              Admin Dashboard
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }}>alaye-agent.live</div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'var(--ink)', color: '#f7f3ec', border: 'none', padding: '8px 18px', borderRadius: 'var(--radius)', fontFamily: 'inherit', fontSize: 13, cursor: 'pointer' }}
          >
            ← Back to Alaye
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)' }}>Loading dashboard…</div>
        ) : (
          <>
            {stats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: '2rem' }}>
                {[
                  { label: 'Total listings', value: stats.total, color: 'var(--ink)' },
                  { label: 'AI agent posts', value: stats.agentPosts, color: '#0f6e56' },
                  { label: 'Community posts', value: stats.communityPosts, color: '#185fa5' },
                  { label: 'Unverified', value: stats.unverified, color: '#d97706' },
                  { label: 'Registered users', value: stats.userCount, color: '#7c3aed' },
                ].map(s => (
                  <div key={s.label} style={{ background: '#fff', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1rem 1.25rem' }}>
                    <div style={{ fontFamily: 'Lora, serif', fontSize: 28, fontWeight: 600, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            )}

            {stats && stats.byType && (
              <div style={{ background: '#fff', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
                <div style={{ fontFamily: 'Lora, serif', fontSize: 15, fontWeight: 500, marginBottom: 12 }}>Listings by type</div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {Object.entries(stats.byType).map(([type, count]) => (
                    <div key={type} style={{ background: '#f2ede6', borderRadius: 20, padding: '4px 14px', fontSize: 13 }}>
                      <strong>{count}</strong> {typeLabels[type] || type}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ background: '#fff', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
              <div style={{ fontFamily: 'Lora, serif', fontSize: 15, fontWeight: 500, marginBottom: 8 }}>AI Agent</div>
              <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12 }}>
                Runs automatically every 12 hours. Click to trigger a manual run now.
              </div>
              <button
                onClick={handleTriggerAgent}
                disabled={triggering}
                style={{ background: 'var(--ink)', color: '#f7f3ec', border: 'none', padding: '8px 18px', borderRadius: 'var(--radius)', fontFamily: 'inherit', fontSize: 13, cursor: triggering ? 'wait' : 'pointer', opacity: triggering ? 0.7 : 1 }}
              >
                {triggering ? 'Triggering…' : '🤖 Run agent now'}
              </button>
              {triggerResult && (
                <div style={{ marginTop: 10, fontSize: 13, color: 'var(--teal)' }}>{triggerResult}</div>
              )}
            </div>

            {users.length > 0 && (
              <div style={{ background: '#fff', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
                <div style={{ fontFamily: 'Lora, serif', fontSize: 15, fontWeight: 500, marginBottom: 12 }}>Registered users</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {users.map((u, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13, padding: '6px 0', borderBottom: '0.5px solid var(--border)' }}>
                      <span>{u.email || 'No email'}</span>
                      <span style={{ color: 'var(--muted)', fontSize: 11 }}>{u.role} · {new Date(u.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ background: '#fff', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '1.25rem 1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: 10 }}>
                <div style={{ fontFamily: 'Lora, serif', fontSize: 15, fontWeight: 500 }}>
                  Listings {selected.size > 0 && <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--muted)' }}>· {selected.size} selected</span>}
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {['all', 'unverified', 'agent', 'community'].map(f => (
                    <button
                      key={f}
                      onClick={() => { setFilter(f); setSelected(new Set()) }}
                      style={{ padding: '5px 12px', borderRadius: 20, border: '0.5px solid var(--border)', background: filter === f ? 'var(--ink)' : '#fff', color: filter === f ? '#f7f3ec' : 'var(--muted)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}
                    >
                      {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {selected.size > 0 && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 12, padding: '10px 12px', background: '#f9f9f7', borderRadius: 'var(--radius)', flexWrap: 'wrap' }}>
                  <button onClick={handleVerifyAll} style={{ background: 'var(--teal)', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 'var(--radius)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                    ✅ Verify {selected.size} selected
                  </button>
                  <button onClick={handleBulkDelete} style={{ background: '#dc2626', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 'var(--radius)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                    🗑️ Delete {selected.size} selected
                  </button>
                  <button onClick={() => setSelected(new Set())} style={{ background: 'none', border: '0.5px solid var(--border)', padding: '6px 14px', borderRadius: 'var(--radius)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', color: 'var(--muted)' }}>
                    Clear selection
                  </button>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, padding: '6px 0', borderBottom: '0.5px solid var(--border)' }}>
                <input
                  type="checkbox"
                  checked={selected.size === filteredListings.length && filteredListings.length > 0}
                  onChange={toggleSelectAll}
                  style={{ cursor: 'pointer' }}
                />
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>Select all ({filteredListings.length})</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {filteredListings.map(l => (
                  <div key={l.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 0', borderBottom: '0.5px solid var(--border)' }}>
                    <input
                      type="checkbox"
                      checked={selected.has(l.id)}
                      onChange={() => toggleSelect(l.id)}
                      style={{ marginTop: 3, cursor: 'pointer', flexShrink: 0 }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--ink)', marginBottom: 2 }}>{l.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {l.institution} · {l.type?.toUpperCase()} · {l.source === 'agent' ? '🤖 Agent' : '👤 Community'}
                        {l.verified && ' · ✅ Verified'}
                        {l.deadline && ` · Due: ${new Date(l.deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button onClick={() => handleVerify(l.id, l.verified)} style={{ background: 'none', border: '0.5px solid var(--border)', borderRadius: 'var(--radius)', padding: '4px 8px', cursor: 'pointer', fontSize: 12, color: l.verified ? '#d97706' : 'var(--teal)' }}>
                        {l.verified ? 'Unverify' : 'Verify'}
                      </button>
                      <button onClick={() => handleDelete(l.id)} style={{ background: 'none', border: '0.5px solid #fecaca', borderRadius: 'var(--radius)', padding: '4px 8px', cursor: 'pointer', fontSize: 12, color: '#dc2626' }}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
      {toast && (
        <div style={{ position: 'fixed', bottom: '2rem', left: '50%', transform: 'translateX(-50%)', background: 'var(--ink)', color: '#f7f3ec', padding: '10px 20px', borderRadius: 'var(--radius)', fontSize: 13, zIndex: 999 }}>
          {toast}
        </div>
      )}
    </div>
  )
}
