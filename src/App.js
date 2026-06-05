import React, { useState, useEffect, useCallback } from 'react'
import { supabase } from './supabaseClient'
import Auth from './Auth'
import './App.css'

const TYPES = [
  { key: 'browse', label: 'All' },
  { key: 'phd', label: 'PhD' },
  { key: 'postdoc', label: 'Postdoc' },
  { key: 'paper', label: 'Paper calls' },
  { key: 'grant', label: 'Grants' },
  { key: 'conf', label: 'Conferences' },
]

const REGIONS = [
  { key: 'all', label: 'All regions' },
  { key: 'africa', label: 'Africa' },
  { key: 'europe', label: 'Europe' },
  { key: 'north america', label: 'North America' },
  { key: 'asia', label: 'Asia' },
  { key: 'global', label: 'Global / remote' },
]

const ADMINS = [
  'areoluwamide@gmail.com'
  'labs@boomsustainable.org'
]

function badgeClass(type) {
  return { phd: 'badge-phd', postdoc: 'badge-postdoc', paper: 'badge-paper', grant: 'badge-grant', conf: 'badge-conf' }[type] || ''
}
function badgeLabel(type) {
  return { phd: 'PhD', postdoc: 'Postdoc', paper: 'Paper call', grant: 'Grant', conf: 'Conference' }[type] || type
}
function daysLeft(deadline) {
  if (!deadline) return null
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24))
}
function timeAgo(dateStr) {
  const d = Math.floor((new Date() - new Date(dateStr)) / (1000 * 60 * 60 * 24))
  if (d === 0) return 'today'
  if (d === 1) return 'yesterday'
  return `${d}d ago`
}

export default function App() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('browse')
  const [region, setRegion] = useState('all')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('newest')
  const [saved, setSaved] = useState(new Set())
  const [modal, setModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [toast, setToast] = useState(null)
  const [session, setSession] = useState(null)
  const [showAuth, setShowAuth] = useState(false)
  const [editListing, setEditListing] = useState(null)
  const [form, setForm] = useState({
    type: 'phd', title: '', institution: '', location: '',
    region: 'global', field: '', deadline: '', funding: '', description: '', link: ''
  })

  const isAdmin = session && ADMINS.includes(session.user.email)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
    return () => subscription.unsubscribe()
  }, [])

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const fetchListings = useCallback(async () => {
    setLoading(true)
    let q = supabase.from('listings').select('*')
    if (tab !== 'browse') q = q.eq('type', tab)
    if (region !== 'all') q = q.ilike('region', `%${region}%`)
    if (query) q = q.or(`title.ilike.%${query}%,institution.ilike.%${query}%,field.ilike.%${query}%,location.ilike.%${query}%`)
    if (sort === 'newest') q = q.order('created_at', { ascending: false })
    else q = q.order('deadline', { ascending: true })
    const { data, error } = await q
    if (!error) setListings(data || [])
    setLoading(false)
  }, [tab, region, query, sort])

  useEffect(() => { fetchListings() }, [fetchListings])

  const handleSave = (id) => {
    setSaved(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id); showToast('Removed from saved') }
      else { next.add(id); showToast('Saved!') }
      return next
    })
  }

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    showToast('Signed out')
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this listing?')) return
    const { error } = await supabase.from('listings').delete().eq('id', id)
    if (!error) { showToast('Listing deleted'); fetchListings() }
    else showToast('Error deleting listing')
  }

  const handleVerify = async (id, current) => {
    const { error } = await supabase.from('listings').update({ verified: !current }).eq('id', id)
    if (!error) { showToast(current ? 'Unverified' : 'Verified!'); fetchListings() }
  }

  const openEdit = (listing) => {
    setEditListing(listing)
    setForm({
      type: listing.type,
      title: listing.title,
      institution: listing.institution,
      location: listing.location || '',
      region: listing.region || 'global',
      field: listing.field || '',
      deadline: listing.deadline || '',
      funding: listing.funding || '',
      description: listing.description || '',
      link: listing.link || '',
    })
    setModal(true)
    setSubmitted(false)
  }

  const handleSubmit = async () => {
    if (!form.title.trim() || !form.institution.trim()) {
      showToast('Please fill in title and institution')
      return
    }
    setSubmitting(true)
    const payload = {
      type: form.type,
      title: form.title.trim(),
      institution: form.institution.trim(),
      location: form.location.trim() || null,
      region: form.region,
      field: form.field.trim() || null,
      deadline: form.deadline || null,
      funding: form.funding.trim() || null,
      description: form.description.trim() || null,
      link: form.link.trim() || null,
    }
    let error
    if (editListing) {
      const res = await supabase.from('listings').update(payload).eq('id', editListing.id)
      error = res.error
    } else {
      const res = await supabase.from('listings').insert([{ ...payload, source: session ? 'community' : 'community', verified: false }])
      error = res.error
    }
    setSubmitting(false)
    if (error) { showToast('Something went wrong. Try again.'); return }
    setSubmitted(true)
    fetchListings()
  }

  const openModal = () => {
    if (!session) { setShowAuth(true); return }
    setEditListing(null)
    setModal(true)
    setSubmitted(false)
    setForm({ type: 'phd', title: '', institution: '', location: '', region: 'global', field: '', deadline: '', funding: '', description: '', link: '' })
  }
  const closeModal = () => { setModal(false); setEditListing(null) }

  return (
    <div className="wrap">
      <div className="hero">
        <div className="hero-top">
          <div>
            <div className="wordmark">Alaye<span>.</span></div>
            <div className="tagline">Open Academic Opportunities · Global</div>
          </div>
          <div className="hero-auth">
            {session ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {isAdmin && <span className="admin-badge"><i className="ti ti-shield-check" aria-hidden="true" /> Admin</span>}
                <span style={{ fontSize: 12, opacity: 0.6 }}>{session.user.email}</span>
                <button className="btn-ghost" onClick={handleSignOut}>Sign out</button>
              </div>
            ) : (
              <button className="btn-ghost" onClick={() => setShowAuth(true)}>Sign in</button>
            )}
          </div>
        </div>
        <div className="hero-desc">PhD positions, postdocs, grants, open paper calls and conferences — in one clean place, for everyone.</div>
        <div className="hero-actions">
          <button className="btn-primary" onClick={openModal}>
            <i className="ti ti-plus" aria-hidden="true" style={{ marginRight: 6 }} />
            Post an opportunity
          </button>
        </div>
        <div className="hero-stats">
          <div><div className="stat-val">{listings.length}</div><div className="stat-lbl">Listings</div></div>
          <div><div className="stat-val">Global</div><div className="stat-lbl">Reach</div></div>
          <div><div className="stat-val">Free</div><div className="stat-lbl">Always open</div></div>
        </div>
      </div>

      <div className="tabs">
        {TYPES.map(t => (
          <button key={t.key} className={`tab${tab === t.key ? ' active' : ''}`} onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>

      <div className="search-row">
        <input
          type="text"
          placeholder="Search by keyword, field, or institution…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && fetchListings()}
        />
        <button className="btn-search" onClick={fetchListings}>
          <i className="ti ti-search" aria-hidden="true" />
        </button>
      </div>

      <div className="filters">
        {REGIONS.map(r => (
          <button key={r.key} className={`chip${region === r.key ? ' active' : ''}`} onClick={() => setRegion(r.key)}>{r.label}</button>
        ))}
      </div>

      <div className="sort-row">
        <span>Sort by</span>
        <select value={sort} onChange={e => setSort(e.target.value)}>
          <option value="newest">Newest first</option>
          <option value="deadline">Deadline soonest</option>
        </select>
      </div>

      <div className="listings">
        {loading ? (
          <div className="loading">Loading opportunities…</div>
        ) : listings.length === 0 ? (
          <div className="empty">
            <i className="ti ti-search-off" aria-hidden="true" />
            <div>No listings yet.</div>
            <button onClick={openModal} style={{ marginTop: 12, background: 'none', border: 'none', color: 'var(--teal)', cursor: 'pointer', fontFamily: 'inherit', fontSize: 14, textDecoration: 'underline' }}>
              Post the first opportunity
            </button>
          </div>
        ) : listings.map(l => {
          const days = daysLeft(l.deadline)
          const urgent = days !== null && days <= 14 && days >= 0
          const isNew = (new Date() - new Date(l.created_at)) < 1000 * 60 * 60 * 48
          return (
            <div key={l.id} className={`card${l.featured ? ' featured' : ''}`}>
              <div className="card-top">
                <div style={{ flex: 1 }}>
                  <div className="badges">
                    <span className={`badge ${badgeClass(l.type)}`}>{badgeLabel(l.type)}</span>
                    {isNew && <span className="badge badge-new">New</span>}
                    {urgent && <span className="badge badge-urgent">{days}d left</span>}
                    {l.verified && <span className="badge badge-verified"><i className="ti ti-circle-check" aria-hidden="true" style={{ fontSize: 11, marginRight: 3 }} />Verified</span>}
                  </div>
                  <div className="card-title">{l.title}</div>
                  <div className="card-inst">{l.institution}</div>
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {isAdmin && (
                    <>
                      <button className="btn-admin" onClick={() => handleVerify(l.id, l.verified)} title={l.verified ? 'Unverify' : 'Verify'}>
                        <i className={`ti ${l.verified ? 'ti-circle-x' : 'ti-circle-check'}`} aria-hidden="true" />
                      </button>
                      <button className="btn-admin" onClick={() => openEdit(l)} title="Edit">
                        <i className="ti ti-edit" aria-hidden="true" />
                      </button>
                      <button className="btn-admin btn-admin-danger" onClick={() => handleDelete(l.id)} title="Delete">
                        <i className="ti ti-trash" aria-hidden="true" />
                      </button>
                    </>
                  )}
                  <button className={`btn-save${saved.has(l.id) ? ' saved' : ''}`} onClick={() => handleSave(l.id)} aria-label="Save listing">
                    <i className="ti ti-bookmark" aria-hidden="true" />
                  </button>
                </div>
              </div>
              <div className="card-meta">
                {l.location && <span className="meta-item"><i className="ti ti-map-pin" aria-hidden="true" />{l.location}</span>}
                {l.field && <span className="meta-item"><i className="ti ti-flask" aria-hidden="true" />{l.field}</span>}
                {l.deadline && <span className="meta-item"><i className="ti ti-calendar" aria-hidden="true" />Deadline: {new Date(l.deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>}
                {l.funding && <span className="meta-item"><i className="ti ti-coin" aria-hidden="true" />{l.funding}</span>}
              </div>
              {l.description && (
                <div style={{ marginTop: 9, fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, borderTop: '0.5px solid var(--border)', paddingTop: 9 }}>
                  {l.description.length > 180 ? l.description.slice(0, 180) + '…' : l.description}
                </div>
              )}
              <div className="card-footer">
                {l.link
                  ? <a className="card-link" href={l.link} target="_blank" rel="noopener noreferrer">View opportunity <i className="ti ti-arrow-up-right" aria-hidden="true" style={{ fontSize: 12 }} /></a>
                  : <span />
                }
                <span className="card-byline">{l.source === 'agent' ? '🤖 AI agent' : '👤 Community'} · {timeAgo(l.created_at)}</span>
              </div>
            </div>
          )
        })}
      </div>

      {showAuth && (
        <div className="overlay" onClick={e => e.target.className === 'overlay' && setShowAuth(false)}>
          <Auth onClose={() => setShowAuth(false)} />
        </div>
      )}

      {modal && (
        <div className="overlay" onClick={e => e.target.className === 'overlay' && closeModal()}>
          <div className="modal">
            {!submitted ? (
              <>
                <div className="modal-hdr">
                  <div className="modal-title">{editListing ? 'Edit listing' : 'Post an opportunity'}</div>
                  <button className="btn-close" onClick={closeModal}><i className="ti ti-x" aria-hidden="true" /></button>
                </div>
                <div className="form-group">
                  <label className="form-label">Type</label>
                  <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
                    <option value="phd">PhD position</option>
                    <option value="postdoc">Postdoc</option>
                    <option value="paper">Open paper call / CFP</option>
                    <option value="grant">Academic grant</option>
                    <option value="conf">Conference</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Title *</label>
                  <input placeholder="e.g. PhD in Computational Linguistics" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Institution / Organisation *</label>
                  <input placeholder="e.g. University of Cape Town" value={form.institution} onChange={e => setForm(f => ({ ...f, institution: e.target.value }))} />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Location</label>
                    <input placeholder="e.g. Lagos, Nigeria" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Region</label>
                    <select value={form.region} onChange={e => setForm(f => ({ ...f, region: e.target.value }))}>
                      <option value="africa">Africa</option>
                      <option value="europe">Europe</option>
                      <option value="north america">North America</option>
                      <option value="asia">Asia</option>
                      <option value="global">Global / remote</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Field / Discipline</label>
                    <input placeholder="e.g. Public Health" value={form.field} onChange={e => setForm(f => ({ ...f, field: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Deadline</label>
                    <input type="date" value={form.deadline} onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))} />
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label">Funding / Stipend</label>
                  <input placeholder="e.g. Fully funded / $25,000/yr" value={form.funding} onChange={e => setForm(f => ({ ...f, funding: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Short description</label>
                  <textarea placeholder="Brief summary of the opportunity and who should apply…" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Application link</label>
                  <input placeholder="https://…" value={form.link} onChange={e => setForm(f => ({ ...f, link: e.target.value }))} />
                </div>
                <button className="btn-submit" onClick={handleSubmit} disabled={submitting}>
                  {submitting ? 'Saving…' : editListing ? 'Save changes →' : 'Post listing →'}
                </button>
              </>
            ) : (
              <div className="success">
                <i className="ti ti-circle-check" aria-hidden="true" />
                <div style={{ fontFamily: 'Lora, serif', fontSize: 18, fontWeight: 500 }}>
                  {editListing ? 'Listing updated!' : 'Listing posted!'}
                </div>
                <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8 }}>Your opportunity is now live on the Alaye board.</p>
                <button className="btn-primary" style={{ marginTop: '1.5rem' }} onClick={closeModal}>Back to listings</button>
              </div>
            )}
          </div>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
