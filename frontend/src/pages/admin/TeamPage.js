import React, { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { AuthContext } from '../../context/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import { 
  Plus, ArrowLeft, Trash2, Shield, BookOpen, Calendar, Receipt, 
  Mail, Clock, X, Send, Loader2, UserPlus, Users, CheckCircle
} from 'lucide-react';
import { API } from '../../config/api';

// Role podle wireframu
const ROLES = [
  { 
    value: 'spravce', 
    label: 'Správce', 
    description: 'Má plný přístup k nastavení a správě dat.',
    icon: Shield,
    color: 'bg-[#2B3E50] text-white'
  },
  { 
    value: 'edukator', 
    label: 'Edukátor', 
    description: 'Může vidět a spravovat doprovodné programy a rezervace.',
    icon: BookOpen,
    color: 'bg-[#4A6FA5] text-white'
  },
  { 
    value: 'lektor', 
    label: 'Externí lektor', 
    description: 'Může se zapisovat k jednotlivým rezervacím.',
    icon: Calendar,
    color: 'bg-[#84A98C] text-white'
  },
  { 
    value: 'pokladni', 
    label: 'Pokladní', 
    description: 'Může ke vzniklým rezervacím doplňovat údaje.',
    icon: Receipt,
    color: 'bg-[#C4AB86] text-white'
  },
  {
    value: 'produkcni',
    label: 'Produkční',
    description: 'Vidí kalendář a rezervace, spravuje blokace. Nemá přístup k platbám ani nastavení.',
    icon: Calendar,
    color: 'bg-[#6D8299] text-white'
  },
  {
    value: 'ucetni',
    label: 'Účetní',
    description: 'Vidí přihlášky a platby, označuje platby jako zaplacené. Neupravuje programy ani tým.',
    icon: Receipt,
    color: 'bg-[#B08968] text-white'
  },
];

export const TeamPage = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  
  // Team members state
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Pending invitations state
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [loadingInvitations, setLoadingInvitations] = useState(true);

  // Phase 83: pending join requests (people asking to be added)
  const [joinRequests, setJoinRequests] = useState([]);
  const [joinReqLoading, setJoinReqLoading] = useState(false);
  const [reviewModal, setReviewModal] = useState({
    open: false,
    request: null,
    action: null,      // "approve" | "reject"
    role: 'edukator',
    note: '',
    submitting: false,
  });
  
  // Dialog states
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  
  // Form states
  const [inviteForm, setInviteForm] = useState({ name: '', email: '', role: 'edukator' });
  const [editForm, setEditForm] = useState({ name: '', role: '' });
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchTeamMembers();
    fetchPendingInvitations();
    fetchJoinRequests();
  }, []);

  const fetchJoinRequests = async () => {
    if (!user?.institution_id) return;
    setJoinReqLoading(true);
    try {
      const res = await axios.get(
        `${API}/institutions/${user.institution_id}/join-requests?status=pending`
      );
      setJoinRequests(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      // 403 (not an admin of this inst) or other → silent — section just hides
      setJoinRequests([]);
    } finally {
      setJoinReqLoading(false);
    }
  };

  const submitReview = async () => {
    const req = reviewModal.request;
    if (!req) return;
    setReviewModal(s => ({ ...s, submitting: true }));
    try {
      if (reviewModal.action === 'approve') {
        const res = await axios.post(
          `${API}/institutions/${user.institution_id}/join-requests/${req.id}/approve`,
          { assigned_role: reviewModal.role }
        );
        const tempPw = res.data?.temp_password;
        toast.success(
          tempPw
            ? `Schváleno. Žadateli odesláno dočasné heslo: ${tempPw}`
            : 'Žádost schválena. Uživatel přidán do týmu.'
        );
      } else {
        await axios.post(
          `${API}/institutions/${user.institution_id}/join-requests/${req.id}/reject`,
          { review_note: reviewModal.note }
        );
        toast.success('Žádost zamítnuta.');
      }
      setReviewModal({ open: false, request: null, action: null, role: 'edukator', note: '', submitting: false });
      await fetchJoinRequests();
      await fetchTeamMembers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Akce se nezdařila');
      setReviewModal(s => ({ ...s, submitting: false }));
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API}/team`);
      setTeamMembers(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      setTeamMembers([{
        id: user?.id,
        name: user?.name || user?.email?.split('@')[0],
        email: user?.email,
        role: 'spravce',
        status: 'active',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingInvitations = async () => {
    try {
      const response = await axios.get(`${API}/invitations/pending`);
      setPendingInvitations(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.log('No pending invitations or endpoint not available');
      setPendingInvitations([]);
    } finally {
      setLoadingInvitations(false);
    }
  };

  const handleSendInvitation = async (e) => {
    e.preventDefault();
    
    if (!inviteForm.email) {
      toast.error('Zadejte email');
      return;
    }
    
    setSending(true);
    try {
      await axios.post(`${API}/invitations/send`, inviteForm);
      toast.success(`Pozvánka byla odeslána na ${inviteForm.email}`);
      setShowInviteDialog(false);
      setInviteForm({ name: '', email: '', role: 'edukator' });
      fetchPendingInvitations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se odeslat pozvánku');
    } finally {
      setSending(false);
    }
  };

  const handleCancelInvitation = async (invitationId) => {
    if (!window.confirm('Opravdu chcete zrušit tuto pozvánku?')) return;
    
    try {
      await axios.delete(`${API}/invitations/${invitationId}`);
      toast.success('Pozvánka byla zrušena');
      fetchPendingInvitations();
    } catch (error) {
      toast.error('Nepodařilo se zrušit pozvánku');
    }
  };

  const handleEditMember = (member) => {
    setEditingMember(member);
    setEditForm({ name: member.name || '', role: member.role });
    setShowEditDialog(true);
  };

  const handleUpdateMember = async (e) => {
    e.preventDefault();
    try {
      // Update name if changed
      if (editForm.name && editForm.name !== editingMember.name) {
        await axios.patch(`${API}/team/${editingMember.id}/name`, { name: editForm.name });
      }
      // Update role if changed
      if (editForm.role !== editingMember.role) {
        await axios.patch(`${API}/team/${editingMember.id}/role`, { role: editForm.role });
      }
      toast.success('Údaje byly aktualizovány');
      setShowEditDialog(false);
      setEditingMember(null);
      fetchTeamMembers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se aktualizovat uživatele');
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm('Opravdu chcete odebrat tohoto uživatele?')) return;
    
    try {
      await axios.delete(`${API}/team/${memberId}`);
      toast.success('Uživatel byl odebrán');
      setShowEditDialog(false);
      setEditingMember(null);
      fetchTeamMembers();
    } catch (error) {
      toast.error('Nepodařilo se odebrat uživatele');
    }
  };

  const getRoleInfo = (roleValue) => {
    const roleMap = { 'admin': 'spravce', 'staff': 'edukator', 'viewer': 'lektor' };
    const mappedRole = roleMap[roleValue] || roleValue;
    return ROLES.find(r => r.value === mappedRole) || ROLES[1];
  };

  const formatExpiryDate = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffHours = Math.round((date - now) / (1000 * 60 * 60));
    
    if (diffHours < 1) return 'Brzy vyprší';
    if (diffHours < 24) return `${diffHours} hodin`;
    return `${Math.round(diffHours / 24)} dní`;
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/admin/settings')} 
              className="p-2 hover:bg-gray-100 rounded-lg"
              data-testid="back-button"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">Správa týmu</h1>
              <p className="text-sm text-gray-500">Spravujte členy týmu a jejich oprávnění</p>
            </div>
          </div>
          <Button 
            onClick={() => setShowInviteDialog(true)}
            className="bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
            data-testid="invite-button"
          >
            <UserPlus className="w-4 h-4 mr-2" />
            Pozvat kolegu
          </Button>
        </div>

        {/* Phase 83: Join requests awaiting review */}
        {joinRequests.length > 0 && (
          <Card className="p-4 md:p-6 border-emerald-200 bg-emerald-50/50" id="join-requests" data-testid="join-requests-section">
            <div className="flex items-center gap-2 mb-4">
              <UserPlus className="w-5 h-5 text-emerald-600" />
              <h2 className="text-lg font-semibold text-slate-900">Žádosti o přijetí do týmu</h2>
              <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-200 text-emerald-800">
                {joinRequests.length}
              </span>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Někdo požádal o přidání do týmu. Vyberte roli a schvalte, nebo žádost zamítněte.
            </p>

            <div className="space-y-3">
              {joinRequests.map((req) => (
                <div
                  key={req.id}
                  className="flex flex-col md:flex-row md:items-center gap-3 p-3 bg-white rounded-lg border border-slate-200"
                  data-testid={`join-request-row-${req.id}`}
                >
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">
                      {req.name || req.email}
                    </div>
                    <div className="text-sm text-slate-500">{req.email}</div>
                    {req.message && (
                      <div className="text-xs italic text-slate-600 mt-1.5 p-2 bg-slate-50 rounded">
                        „{req.message}"
                      </div>
                    )}
                    <div className="text-xs text-slate-400 mt-1">
                      {new Date(req.created_at).toLocaleString('cs-CZ')}
                    </div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <Button
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      data-testid={`join-request-approve-${req.id}`}
                      onClick={() => setReviewModal({
                        open: true, request: req, action: 'approve',
                        role: 'edukator', note: '', submitting: false,
                      })}
                    >
                      Schválit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-red-600 border-red-200 hover:bg-red-50"
                      data-testid={`join-request-reject-${req.id}`}
                      onClick={() => setReviewModal({
                        open: true, request: req, action: 'reject',
                        role: 'edukator', note: '', submitting: false,
                      })}
                    >
                      Zamítnout
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Pending Invitations */}
        {pendingInvitations.length > 0 && (
          <Card className="p-4 md:p-6 border-amber-200 bg-amber-50/50">
            <div className="flex items-center gap-2 mb-4">
              <Mail className="w-5 h-5 text-amber-600" />
              <h2 className="text-lg font-semibold text-slate-900">Čekající pozvánky</h2>
              <span className="px-2 py-0.5 text-xs rounded-full bg-amber-200 text-amber-800">
                {pendingInvitations.length}
              </span>
            </div>
            
            <div className="space-y-3">
              {pendingInvitations.map((invitation) => {
                const roleInfo = getRoleInfo(invitation.role);
                return (
                  <div 
                    key={invitation.id} 
                    className="flex items-center justify-between p-3 bg-white border border-amber-200 rounded-lg"
                    data-testid={`pending-invitation-${invitation.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                        <Mail className="w-5 h-5 text-amber-600" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">
                          {invitation.name || invitation.email}
                        </p>
                        <p className="text-sm text-gray-500">{invitation.email}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${roleInfo.color}`}>
                            {roleInfo.label}
                          </span>
                          <span className="flex items-center gap-1 text-xs text-gray-500">
                            <Clock className="w-3 h-3" />
                            Vyprší za {formatExpiryDate(invitation.expires_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleCancelInvitation(invitation.id)}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="Zrušit pozvánku"
                      data-testid={`cancel-invitation-${invitation.id}`}
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* Active Team Members */}
        <Card className="p-4 md:p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-[#4A6FA5]" />
            <h2 className="text-lg font-semibold text-slate-900">Aktivní členové</h2>
            <span className="px-2 py-0.5 text-xs rounded-full bg-[#4A6FA5]/10 text-[#4A6FA5]">
              {teamMembers.length}
            </span>
          </div>

          {loading ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-[#4A6FA5] mx-auto" />
            </div>
          ) : (
            <div className="space-y-3">
              {teamMembers.map((member) => {
                const roleInfo = getRoleInfo(member.role);
                const isCurrentUser = member.id === user?.id;
                const Icon = roleInfo.icon;
                
                return (
                  <div 
                    key={member.id} 
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                    data-testid={`team-member-${member.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full ${roleInfo.color} flex items-center justify-center`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-slate-900">
                            {member.name || member.email?.split('@')[0]}
                          </p>
                          {isCurrentUser && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">
                              Vy
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${roleInfo.color}`}>
                            {roleInfo.label}
                          </span>
                          <span className="flex items-center gap-1 text-xs text-green-600">
                            <CheckCircle className="w-3 h-3" />
                            Aktivní
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {!isCurrentUser && (
                      <button
                        onClick={() => handleEditMember(member)}
                        className="text-[#4A6FA5] text-sm font-medium hover:underline"
                        data-testid={`edit-member-${member.id}`}
                      >
                        Upravit
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Roles Description */}
        <Card className="p-4 md:p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Role a oprávnění</h2>
          <p className="text-sm text-gray-500 mb-4">Přehled dostupných rolí v systému</p>
          
          <div className="grid gap-4 md:grid-cols-2">
            {ROLES.map(role => {
              const Icon = role.icon;
              return (
                <div key={role.value} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className={`w-8 h-8 rounded-lg ${role.color} flex items-center justify-center flex-shrink-0`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-medium text-slate-900">{role.label}</h3>
                    <p className="text-sm text-gray-500">{role.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Invite Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-[#4A6FA5]" />
              Pozvat nového kolegu
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSendInvitation} className="space-y-6" data-testid="invite-form">
            <div className="space-y-4">
              <div>
                <Label htmlFor="invite-name">Jméno a příjmení</Label>
                <Input
                  id="invite-name"
                  value={inviteForm.name}
                  onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
                  placeholder="Jana Nováková"
                  className="mt-1"
                  data-testid="invite-name-input"
                />
              </div>

              <div>
                <Label htmlFor="invite-email">Email *</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  placeholder="jana.novakova@instituce.cz"
                  required
                  className="mt-1"
                  data-testid="invite-email-input"
                />
              </div>
            </div>

            <div className="space-y-3">
              <Label>Role</Label>
              {ROLES.map(role => {
                const Icon = role.icon;
                return (
                  <label 
                    key={role.value} 
                    className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      inviteForm.role === role.value 
                        ? 'border-[#4A6FA5] bg-[#4A6FA5]/5' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="invite-role"
                      value={role.value}
                      checked={inviteForm.role === role.value}
                      onChange={() => setInviteForm({ ...inviteForm, role: role.value })}
                      className="mt-1"
                      data-testid={`invite-role-${role.value}`}
                    />
                    <Icon className={`w-5 h-5 mt-0.5 ${inviteForm.role === role.value ? 'text-[#4A6FA5]' : 'text-gray-400'}`} />
                    <div>
                      <p className="font-medium text-slate-900">{role.label}</p>
                      <p className="text-sm text-gray-500">{role.description}</p>
                    </div>
                  </label>
                );
              })}
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
              <p>Pozvánka bude odeslána na zadaný email. Příjemce bude mít 48 hodin na její přijetí.</p>
            </div>

            <div className="flex gap-2">
              <Button 
                type="button"
                variant="outline"
                onClick={() => setShowInviteDialog(false)}
                className="flex-1"
              >
                Zrušit
              </Button>
              <Button 
                type="submit" 
                disabled={sending || !inviteForm.email}
                className="flex-1 bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
                data-testid="send-invite-button"
              >
                {sending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Odesílám...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Odeslat pozvánku
                  </>
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Member Dialog */}
      <Dialog open={showEditDialog} onOpenChange={(open) => { setShowEditDialog(open); if (!open) setEditingMember(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Upravit člena týmu</DialogTitle>
          </DialogHeader>
          
          {editingMember && (
            <form onSubmit={handleUpdateMember} className="space-y-6" data-testid="edit-form">
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">{editingMember.email}</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-name">Jméno a příjmení</Label>
                <Input
                  id="edit-name"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  placeholder="Jan Novák"
                  data-testid="edit-name-input"
                />
              </div>

              <div className="space-y-3">
                <Label>Změnit roli</Label>
                {ROLES.map(role => {
                  const Icon = role.icon;
                  return (
                    <label 
                      key={role.value} 
                      className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                        editForm.role === role.value 
                          ? 'border-[#4A6FA5] bg-[#4A6FA5]/5' 
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="edit-role"
                        value={role.value}
                        checked={editForm.role === role.value}
                        onChange={() => setEditForm({ ...editForm, role: role.value })}
                        className="mt-1"
                        data-testid={`edit-role-${role.value}`}
                      />
                      <Icon className={`w-5 h-5 mt-0.5 ${editForm.role === role.value ? 'text-[#4A6FA5]' : 'text-gray-400'}`} />
                      <div>
                        <p className="font-medium text-slate-900">{role.label}</p>
                        <p className="text-sm text-gray-500">{role.description}</p>
                      </div>
                    </label>
                  );
                })}
              </div>

              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleRemoveMember(editingMember.id)}
                  className="text-red-500 border-red-200 hover:bg-red-50"
                  data-testid="remove-member-button"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Odebrat
                </Button>
                <Button 
                  type="submit" 
                  className="flex-1 bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
                  data-testid="save-member-button"
                >
                  Uložit změny
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Phase 83: review modal for join requests */}
      {reviewModal.open && reviewModal.request && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" data-testid="review-modal">
          <Card className="w-full max-w-md bg-white p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-1">
              {reviewModal.action === 'approve' ? 'Schválit žádost' : 'Zamítnout žádost'}
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              {reviewModal.request.name || reviewModal.request.email} <br />
              <span className="text-xs">{reviewModal.request.email}</span>
            </p>

            {reviewModal.action === 'approve' ? (
              <div className="mb-4">
                <Label>Přidělit roli</Label>
                <Select
                  value={reviewModal.role}
                  onValueChange={(v) => setReviewModal(s => ({ ...s, role: v }))}
                >
                  <SelectTrigger className="mt-2" data-testid="review-role-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map(r => (
                      <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div className="mb-4">
                <Label htmlFor="review-note">Důvod zamítnutí (volitelné — odešleme žadateli)</Label>
                <Textarea
                  id="review-note"
                  data-testid="review-note"
                  className="mt-2"
                  rows={3}
                  placeholder="Např. Tento účet k naší instituci nepatří."
                  value={reviewModal.note}
                  onChange={(e) => setReviewModal(s => ({ ...s, note: e.target.value }))}
                  maxLength={500}
                />
              </div>
            )}

            <div className="flex gap-2">
              <Button
                variant="ghost"
                className="flex-1"
                data-testid="review-cancel-btn"
                disabled={reviewModal.submitting}
                onClick={() => setReviewModal({ open: false, request: null, action: null, role: 'edukator', note: '', submitting: false })}
              >
                Zpět
              </Button>
              <Button
                className={`flex-1 ${reviewModal.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'} text-white`}
                data-testid="review-submit-btn"
                disabled={reviewModal.submitting}
                onClick={submitReview}
              >
                {reviewModal.submitting ? '...' : (reviewModal.action === 'approve' ? 'Schválit' : 'Zamítnout')}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </AdminLayout>
  );
};
