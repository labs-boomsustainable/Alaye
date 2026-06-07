import React, { useState, useEffect, useCallback } from 'react'
import { supabase } from './supabaseClient'
import Auth from './Auth'
import Cart from './Cart'
import Admin from './Admin'
import './App.css'

const TYPES = [
  { key: 'browse', label: 'All' },
  { key: 'phd', label: 'PhD' },
  { key: 'msc', label: 'MSc' },
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
]

function badgeClass(type) {
  return { phd: 'badge-phd', msc: 'badge-msc', postdoc: 'badge-postdoc', paper: 'badge-paper', grant: 'badge-grant', conf: 'badge-conf' }[type] || ''
}
function badgeLabel(type) {
  return { phd: 'PhD', msc: 'MSc', postdoc: 'Postdoc', paper: 'Paper call', grant: 'Grant', conf: 'Conference' }[type] || type
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
  const [modal, setModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [toast, setToast] = useState(null)
  const [session, setSession] = useState(null)
  const [showAuth, setShowAuth] = useState(false)
  const [showCart, setShowCart] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)
  const [showBanner, setShowBanner] = useState(() => !localStorage.getItem('alaye_visited'))
  const [editListing, setEditListing] = useState(null)
  const [bookmarks, setBookmarks] = useState(new Set())
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('alaye_email') || '')
  const [emailPrompt, setEmailPrompt] = useState(null)
  const [emailInput, setEmailInput] = useState('')
  const [form, setForm] = useState({
    type: 'phd', title: '', institution: '', location: '',
    region: 'global', field: '', deadline: '', funding: '', description: '', link: ''
  })

  const isAdmin = session && ADMINS.includes(session.user.email)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setSession(session)
      if (event === 'SIGNED_IN') window.history.replaceState({}, document.title, '/')
    })
    return () => subscription.unsubscribe()
  }, [])

  const fetchBookmarks = useCallback(async () => {
    if (!userEmail) { setBookmarks(new Set()); return }
    const { data } = await supabase
      .from('subscribers')
      .select('listing_id')
      .eq('email', userEmail)
    if (data) setBookmarks(new Set(data.map(b => b.listing_id)))
  }, [userEmail])

  useEffect(() => { fetchBookmarks() }, [fetchBookmarks])

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

  const handleBookmark = async (id) => {
    if (!userEmail) {
      setEmailPrompt(id)
      setEmailInput('')
      return
    }
    if (bookmarks.has(id)) {
      await supabase.from('subscribers').delete().eq('listing_id', id).eq('email', userEmail)
      setBookmarks(prev => { const n = new Set(prev); n.delete(id); return n })
      showToast('Removed from saved')
    } else {
      await supabase.from('subscribers').insert([{ email: userEmail, listing_id: id }])
      setBookmarks(prev => new Set([...prev, id]))
      showToast('Saved! You will get deadline reminders.')
    }
  }

  const handleEmailSubmit = async () => {
    const email = emailInput.trim().toLowerCase()
    if (!email || !email.includes('@')) { showToast('Please enter a valid email'); return }
    localStorage.setItem('alaye_email', email)
    setUserEmail(email)
    await supabase.from('subscribers').insert([{ email, listing_id: emailPrompt }])
    setBookmarks(prev => new Set([...prev, emailPrompt]))
    setEmailPrompt(null)
    showToast('Saved! You will get deadline reminders.')
  }

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    showToast('Signed out')
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this listing?')) return
    const { error } = await supabase.from('listings').delete().eq('id', id)
    if (!error) { showToast('Listing deleted'); fetchListings() }
  }

  const handleVerify = async (id, current) => {
    const { error } = await supabase.from('listings').update({ verified: !current }).eq('id', id)
    if (!error) { showToast(current ? 'Unverified' : 'Verified!'); fetchListings() }
  }

  const openEdit = (listing) => {
    setEditListing(listing)
    setForm({
      type: listing.type, title: listing.title,
      institution: listing.institution, location: listing.location || '',
      region: listing.region || 'global', field: listing.field || '',
      deadline: listing.deadline || '', funding: listing.funding || '',
      description: listing.description || '', link: listing.link || '',
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
      type: form.type, title: form.title.trim(),
      institution: form.institution.trim(), location: form.location.trim() || null,
      region: form.region, field: form.field.trim() || null,
      deadline: form.deadline || null, funding: form.funding.trim() || null,
      description: form.description.trim() || null, link: form.link.trim() || null,
    }
    let error
    if (editListing) {
      const res = await supabase.from('listings').update(payload).eq('id', editListing.id)
      error = res.error
    } else {
      const res = await supabase.from('listings').insert([{ ...payload, source: 'community', verified: false }])
      error = res.error
    }
    setSubmitting(false)
    if (error) { showToast('Something went wrong. Try again.'); return }
    setSubmitted(true)
    fetchListings()
  }

  const handleDismissBanner = () => {
    localStorage.setItem('alaye_visited', 'true')
    setShowBanner(false)
  }

  const handleShare = (listing) => {
    const text = `${listing.title} at ${listing.institution} — via Alaye`
    const url = `https://alaye-agent.live`
    if (navigator.share) {
      navigator.share({ title: listing.title, text, url })
    } else {
      navigator.clipboard.writeText(`${text}\n${url}`)
      showToast('Link copied to clipboard!')
    }
  }

  const openModal = () => {
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
                {isAdmin && (
                  <button
                    onClick={() => setShowAdmin(true)}
                    style={{ background: 'var(--gold-lt)', color: 'var(--gold)', border: 'none', padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 4 }}
                  >
                    <i className="ti ti-shield-check" aria-hidden="true" /> Admin
                  </button>
                )}
                <button className="cart-btn" onClick={() => setShowCart(true)}>
                  <i className="ti ti-bookmark" aria-hidden="true" />
                  {bookmarks.size > 0 && <span className="cart-count">{bookmarks.size}</span>}
                </button>
                <span style={{ fontSize: 12, opacity: 0.6 }}>{session.user.email}</span>
                <button className="btn-ghost" onClick={handleSignOut}>Sign out</button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {userEmail && (
                  <button className="cart-btn" onClick={() => setShowCart(true)}>
                    <i className="ti ti-bookmark" aria-hidden="true" />
                    {bookmarks.size > 0 && <span className="cart-count">{bookmarks.size}</span>}
                  </button>
                )}
                <button className="btn-ghost" onClick={() => setShowAuth(true)}>Admin login</button>
              </div>
            )}
          </div>
        </div>
        <div className="hero-desc">A public access group for unconventional academic opportunities — those that live inside closed networks, fellowships, alumni circles, and youth communities, now open to everyone.</div>
        <div className="hero-actions">
          <button className="btn-primary" onClick={openModal}>
            <i className="ti ti-plus" aria-hidden="true" style={{ marginRight: 6 }} />
            Post an opportunity
          </button>
        </div>
        <div className="hero-stats">
          <div><div className="stat-val">{listings.length}</div><div className="stat-lbl">Listings</div></div>
          <div><div className="stat-val">Global</div><div className="stat-lbl">Reach</div></div>
          <div><div className="stat-val">Free</div><div className="stat-lbl">Open source</div></div>
        </div>
      </div>

      {showBanner && (
        <div className="onboarding-banner">
          <p>
            <strong>Welcome to Alaye.</strong> A public access group for unconventional academic opportunities — those that live inside closed networks, fellowships, alumni circles, and youth communities, now open to everyone. Click the bookmark icon on any listing to save it and get deadline reminders.
          </p>
          <button onClick={handleDismissBanner}>Got it ✓</button>
        </div>
      )}

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
          const isBookmarked = bookmarks.has(l.id)
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
                  <button
                    className={`btn-save${isBookmarked ? ' saved' : ''}`}
                    onClick={() => handleBookmark(l.id)}
                    title={isBookmarked ? 'Remove from saved' : 'Save this opportunity'}
                  >
                    <i className={`ti ${isBookmarked ? 'ti-bookmark-filled' : 'ti-bookmark'}`} aria-hidden="true" />
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
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className="card-byline">{l.source === 'agent' ? '🤖 AI agent' : '👤 Community'} · {timeAgo(l.created_at)}</span>
                  <button
                    onClick={() => handleShare(l)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: 'var(--muted)', padding: 0 }}
                    title="Share this opportunity"
                  >
                    <i className="ti ti-share" aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {emailPrompt && (
        <div className="overlay" onClick={e => e.target.className === 'overlay' && setEmailPrompt(null)}>
          <div className="modal" style={{ maxWidth: 420 }}>
            <div className="modal-hdr">
              <div className="modal-title">Save this opportunity</div>
              <button className="btn-close" onClick={() => setEmailPrompt(null)}><i className="ti ti-x" aria-hidden="true" /></button>
            </div>
            <p style={{ fontSize: 14, color: 'var(--muted)', marginBottom: '1.25rem', lineHeight: 1.6 }}>
              Enter your email to save this opportunity and receive deadline reminders. No password needed.
            </p>
            <div className="form-group">
              <label className="form-label">Your email</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleEmailSubmit()}
                autoFocus
              />
            </div>
            <button className="btn-submit" onClick={handleEmailSubmit}>
              Save opportunity →
            </button>
            <p style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', marginTop: 12 }}>
              We only use your email for deadline reminders. No spam.
            </p>
          </div>
        </div>
      )}

      {showAuth && (
        <div className="overlay" onClick={e => e.target.className === 'overlay' && setShowAuth(false)}>
          <Auth onClose={() => setShowAuth(false)} />
        </div>
      )}

      {showCart && (
        <div className="overlay" onClick={e => e.target.className === 'overlay' && setShowCart(false)}>
          <Cart
            userEmail={userEmail}
            session={session}
            bookmarks={bookmarks}
            onClose={() => setShowCart(false)}
            onRemove={(id) => {
              setBookmarks(prev => { const n = new Set(prev); n.delete(id); return n })
            }}
          />
        </div>
      )}

      {showAdmin && (
        <Admin onClose={() => setShowAdmin(false)} />
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
                    <option value="msc">MSc / Masters</option>
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
                <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8 }}>Your opportunity is now live on Alaye.</p>
                <button className="btn-primary" style={{ marginTop: '1.5rem' }} onClick={closeModal}>Back to listings</button>
              </div>
            )}
          </div>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}

      <div className="alaye-footer">
        <div style={{ marginBottom: 6 }}>
          <strong style={{ fontFamily: 'Lora, serif' }}>Alaye<span style={{ color: 'var(--gold)' }}>.</span></strong>
          {' '}— Global Academic Opportunities
        </div>
        <div>
          Free & open source ·{' '}
          <a href="https://github.com/labs-boomsustainable/Alaye" target="_blank" rel="noopener noreferrer">GitHub</a>
          {' '}·{' '}
          <a href="mailto:labs@boomsustainable.org">Contact</a>
          {' '}·{' '}
          Built by <a href="https://boomsustainable.org" target="_blank" rel="noopener noreferrer">Boom Sustainable</a>
        </div>
      </div>
    </div>
  )
}
