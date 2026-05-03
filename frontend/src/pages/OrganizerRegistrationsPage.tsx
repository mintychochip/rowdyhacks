import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import {
  getOrganizerRegistrations,
  acceptRegistration,
  rejectRegistration,
  checkinRegistration,
  getHackathons,
} from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { WaitlistManager } from '../components/WaitlistManager';
import { PRIMARY, ERROR, ERROR_BG20, ERROR_TEXT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DIM, INPUT_BG, INPUT_BORDER, BORDER_LIGHT, SUCCESS, STATUS_PENDING, STATUS_ACCEPTED, STATUS_REJECTED, INFO } from '../theme';

interface Registration {
  id: string;
  user_name?: string;
  user_email?: string;
  team_name?: string;
  status: string;
  registered_at: string;
}

export default function OrganizerRegistrationsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isMobile } = useMediaQuery();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [total, setTotal] = useState(0);
  const [hackathonName, setHackathonName] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const limit = 20;

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [regData] = await Promise.all([
        getOrganizerRegistrations(id, { status: statusFilter || undefined, offset, limit }),
        getHackathons().then(hacks => {
          const found = (hacks || []).find((h: any) => h.id === id);
          if (found) setHackathonName(found.name);
        }).catch(() => {}),
      ]);
      setRegistrations(regData.registrations || []);
      setTotal(regData.total || 0);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  }, [id, statusFilter, offset]);

  useEffect(() => { load(); }, [load]);

  const handleAccept = async (regId: string) => {
    if (!id) return;
    try {
      await acceptRegistration(id, regId);
      load();
    } catch {}
  };

  const handleReject = async (regId: string) => {
    if (!id) return;
    try {
      await rejectRegistration(id, regId);
      load();
    } catch {}
  };

  const handleCheckin = async (regId: string) => {
    if (!id) return;
    try {
      await checkinRegistration(id, regId);
      load();
    } catch {}
  };

  if (!user || user.role !== 'organizer') {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60, color: TEXT_MUTED }}>
        Organizer access required.
      </div>
    );
  }

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  // Calculate status counts from loaded registrations for display
  const pendingCount = registrations.filter(r => r.status === 'pending').length;
  const acceptedCount = registrations.filter(r => r.status === 'accepted').length;
  const waitlistCount = registrations.filter(r => r.status === 'waitlisted').length;
  const checkedInCount = registrations.filter(r => r.status === 'checked_in').length;
  const rejectedCount = registrations.filter(r => r.status === 'rejected').length;

  // Filter definitions with counts
  const FILTERS = [
    { key: '', label: 'All', count: total },
    { key: 'pending', label: 'Pending', count: pendingCount },
    { key: 'accepted', label: 'Accepted', count: acceptedCount },
    { key: 'waitlisted', label: 'Waitlist', count: waitlistCount },
    { key: 'checked_in', label: 'Checked In', count: checkedInCount },
    { key: 'rejected', label: 'Rejected', count: rejectedCount },
  ];

  const STATS_MAP = [
    { label: 'Total', value: total, color: TEXT_MUTED },
    { label: 'Pending', value: pendingCount, color: STATUS_PENDING },
    { label: 'Accepted', value: acceptedCount, color: STATUS_ACCEPTED },
    { label: 'Waitlist', value: waitlistCount, color: INFO },
    { label: 'Checked In', value: checkedInCount, color: SUCCESS },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? 14 : 40 }}>
      <button
        onClick={() => navigate('/hackathons')}
        style={{
          background: 'none',
          border: `1px solid ${INPUT_BORDER}`,
          borderRadius: 6,
          padding: '6px 14px',
          color: TEXT_MUTED,
          cursor: 'pointer',
          fontSize: 13,
          marginBottom: 20,
        }}
      >
        &larr; Back to Hackathons
      </button>

      <h1 style={{ fontSize: 24, marginBottom: 4 }} data-mobile-h1>
        {hackathonName || 'Registrations'}
      </h1>
      <p style={{ fontSize: 13, color: TEXT_MUTED, marginBottom: 20 }}>
        Manage participant registrations
      </p>

      {error && (
        <div style={{
          background: ERROR_BG20,
          border: `1px solid ${ERROR}`,
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
          color: ERROR_TEXT,
          fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {/* Stats Summary */}
      {total > 0 && (
        <div style={{
          display: 'flex',
          gap: 12,
          marginBottom: 20,
          flexWrap: 'wrap',
        }}>
          {STATS_MAP.map(stat => (
            <div
              key={stat.label}
              style={{
                background: INPUT_BG,
                border: `1px solid ${BORDER_LIGHT}`,
                borderRadius: 10,
                padding: '14px 20px',
                textAlign: 'center',
                flex: '1 1 100px',
                minWidth: 100,
              }}
            >
              <div style={{ fontSize: 24, fontWeight: 700, color: stat.color }}>
                {stat.value}
              </div>
              <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filter Buttons */}
      <div style={{ marginBottom: 20, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => { setStatusFilter(f.key); setOffset(0); }}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: `1px solid ${INPUT_BORDER}`,
              background: statusFilter === f.key ? PRIMARY : 'transparent',
              color: statusFilter === f.key ? '#fff' : TEXT_MUTED,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {f.label} ({f.count})
          </button>
        ))}
      </div>

      {statusFilter === 'waitlisted' && id && (
        <WaitlistManager hackathonId={id} />
      )}

      {statusFilter !== 'waitlisted' && loading && (
        <div style={{ color: TEXT_MUTED, textAlign: 'center', padding: isMobile ? 20 : 40 }}>
          Loading...
        </div>
      )}

      {statusFilter !== 'waitlisted' && !loading && registrations.length === 0 && (
        <div style={{ textAlign: 'center', padding: isMobile ? 20 : 40, color: TEXT_MUTED }}>
          No registrations found.
        </div>
      )}

      {statusFilter !== 'waitlisted' && !loading && registrations.map(reg => (
        <div
          key={reg.id}
          style={{
            background: INPUT_BG,
            border: `1px solid ${BORDER_LIGHT}`,
            borderRadius: 10,
            padding: 14,
            marginBottom: 8,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 8,
          }}
        >
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontWeight: 600 }}>
              {reg.user_name || 'Unknown'}
            </div>
            <div style={{ fontSize: 13, color: TEXT_MUTED }}>
              {reg.user_email || ''}
            </div>
            {reg.team_name && (
              <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginTop: 2 }}>
                Team: {reg.team_name}
              </div>
            )}
            <div style={{ fontSize: 12, color: TEXT_DIM, marginTop: 2 }}>
              {new Date(reg.registered_at).toLocaleDateString()}
            </div>
          </div>

          <StatusBadge status={reg.status} />

          <div style={{ display: 'flex', gap: 6 }}>
            {reg.status === 'pending' && (
              <>
                <button
                  onClick={() => handleAccept(reg.id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    border: 'none',
                    background: STATUS_ACCEPTED,
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  Accept
                </button>
                <button
                  onClick={() => handleReject(reg.id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    border: 'none',
                    background: STATUS_REJECTED,
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  Reject
                </button>
              </>
            )}
            {reg.status === 'accepted' && (
              <button
                onClick={() => handleCheckin(reg.id)}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  border: 'none',
                  background: INFO,
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                Check In
              </button>
            )}
          </div>
        </div>
      ))}

      {/* Pagination */}
      {statusFilter !== 'waitlisted' && totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 20 }}>
          <button
            disabled={offset === 0}
            onClick={() => setOffset(o => Math.max(0, o - limit))}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: `1px solid ${INPUT_BORDER}`,
              background: 'transparent',
              color: offset === 0 ? TEXT_DIM : TEXT_MUTED,
              cursor: offset === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            Prev
          </button>
          <span style={{ padding: '6px 0', color: TEXT_MUTED, fontSize: 13 }}>
            Page {currentPage} of {totalPages}
          </span>
          <button
            disabled={offset + limit >= total}
            onClick={() => setOffset(o => o + limit)}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: `1px solid ${INPUT_BORDER}`,
              background: 'transparent',
              color: offset + limit >= total ? TEXT_DIM : TEXT_MUTED,
              cursor: offset + limit >= total ? 'not-allowed' : 'pointer',
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
