import React, { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { AuthContext } from '../../context/AuthContext';
import { toast } from 'sonner';
import axios from 'axios';
import { Plus, ArrowLeft, Trash2, Shield, BookOpen, Calendar, Receipt } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
    label: 'Uživatel/ Edukator', 
    description: 'Může vidět a spravovat doprovodné programy a rezervace.',
    icon: BookOpen,
    color: 'bg-[#4A6FA5] text-white'
  },
  { 
    value: 'lektor', 
    label: 'Uživatel/ Externí lektor', 
    description: 'Může se zapisovat k jednotlivým rezervacím.',
    icon: Calendar,
    color: 'bg-[#84A98C] text-white'
  },
  { 
    value: 'pokladni', 
    label: 'Uživatel/ Pokladní', 
    description: 'Může ke vzniklým rezervacím doplňovat údaje.',
    icon: Receipt,
    color: 'bg-[#C4AB86] text-white'
  },
];

export const TeamPage = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    role: 'edukator',
  });

  useEffect(() => {
    fetchTeamMembers();
  }, []);

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API}/team`);
      setTeamMembers(response.data);
    } catch (error) {
      // If endpoint doesn't exist yet, show current user only
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingMember) {
        await axios.patch(`${API}/team/${editingMember.id}`, formData);
        toast.success('Uživatel byl aktualizován');
      } else {
        await axios.post(`${API}/team/invite`, formData);
        toast.success('Uživatel byl přidán');
      }
      setShowAddDialog(false);
      setEditingMember(null);
      resetForm();
      fetchTeamMembers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se uložit uživatele');
    }
  };

  const handleEdit = (member) => {
    setEditingMember(member);
    setFormData({
      name: member.name || '',
      email: member.email,
      role: member.role,
    });
    setShowAddDialog(true);
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm('Opravdu chcete odebrat tohoto uživatele?')) return;
    
    try {
      await axios.delete(`${API}/team/${memberId}`);
      toast.success('Uživatel byl odebrán');
      fetchTeamMembers();
    } catch (error) {
      toast.error('Nepodařilo se odebrat uživatele');
    }
  };

  const resetForm = () => {
    setFormData({ name: '', email: '', role: 'edukator' });
    setEditingMember(null);
  };

  const getRoleInfo = (roleValue) => {
    // Map old roles to new ones
    const roleMap = {
      'admin': 'spravce',
      'staff': 'edukator',
      'viewer': 'lektor',
    };
    const mappedRole = roleMap[roleValue] || roleValue;
    return ROLES.find(r => r.value === mappedRole) || ROLES[1];
  };

  // Render member list view
  const renderMemberList = () => (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/admin/settings')} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-900">Správa uživatelů</h1>
      </div>

      {/* Users section */}
      <Card className="p-4 md:p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Uživatelé</h2>
            <p className="text-sm text-gray-500">Můžete přidat nebo odebraz uživatele i jejich oprávnění.</p>
          </div>
          <Button 
            onClick={() => { resetForm(); setShowAddDialog(true); }}
            className="bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
            data-testid="add-user-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Přidat
          </Button>
        </div>

        {/* Team members list */}
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4A6FA5] mx-auto"></div>
          </div>
        ) : (
          <div className="space-y-3">
            {teamMembers.map((member) => {
              const roleInfo = getRoleInfo(member.role);
              const isCurrentUser = member.id === user?.id;
              
              return (
                <div 
                  key={member.id} 
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
                  data-testid={`team-member-${member.id}`}
                >
                  <div>
                    <p className="font-medium text-slate-900">
                      {member.name || member.email?.split('@')[0]}
                    </p>
                    <p className="text-sm text-gray-500">{member.email}</p>
                    <div className="flex gap-2 mt-2">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${roleInfo.color}`}>
                        {roleInfo.label.split('/')[0].trim()}
                      </span>
                      <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-700">
                        {member.status === 'active' ? 'aktivní' : 'neaktivní'}
                      </span>
                    </div>
                  </div>
                  
                  {!isCurrentUser && (
                    <button
                      onClick={() => handleEdit(member)}
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

      {/* Roles description */}
      <Card className="p-4 md:p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-2">Uživatelé a oprávnění</h2>
        <p className="text-sm text-gray-500 mb-4">Můžete přidat nebo odebraz uživatele i jejich oprávnění.</p>
        
        <div className="space-y-4">
          {ROLES.map(role => (
            <div key={role.value}>
              <h3 className="font-medium text-slate-900">{role.label}</h3>
              <p className="text-sm text-gray-500">{role.description}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );

  // Render add/edit user form
  const renderUserForm = () => (
    <Dialog open={showAddDialog} onOpenChange={(open) => { setShowAddDialog(open); if (!open) resetForm(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-4">
            <button onClick={() => setShowAddDialog(false)} className="p-2 hover:bg-gray-100 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <DialogTitle>{editingMember ? 'Upravit uživatele' : 'Nový uživatel'}</DialogTitle>
          </div>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-6" data-testid="user-form">
          {/* Základní informace */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Základní informace</h3>
            
            <div>
              <Label htmlFor="name">Jméno a Příjmení</Label>
              <Input
                id="name"
                data-testid="user-name-input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Jana Nováková"
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                data-testid="user-email-input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="jana.novakova@galerie.cz"
                required
                disabled={!!editingMember}
                className="mt-2"
              />
            </div>
          </div>

          {/* Role a oprávnění */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Role a oprávnění</h3>
            
            <div className="space-y-3">
              {ROLES.map(role => {
                const Icon = role.icon;
                return (
                  <label 
                    key={role.value} 
                    className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                      formData.role === role.value 
                        ? 'border-[#4A6FA5] bg-[#4A6FA5]/5' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="role"
                      value={role.value}
                      checked={formData.role === role.value}
                      onChange={() => setFormData({ ...formData, role: role.value })}
                      className="mt-1"
                      data-testid={`role-${role.value}`}
                    />
                    <div>
                      <p className="font-medium text-slate-900">{role.label}</p>
                      <p className="text-sm text-gray-500">{role.description}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button 
              type="submit" 
              className="flex-1 bg-[#2B3E50] text-white hover:bg-[#1e2d3a]"
              data-testid="save-user-button"
            >
              Uložit
            </Button>
            {editingMember && (
              <Button
                type="button"
                variant="outline"
                onClick={() => handleRemoveMember(editingMember.id)}
                className="text-red-500 border-red-200 hover:bg-red-50"
                data-testid="delete-user-button"
              >
                <Trash2 className="w-5 h-5" />
              </Button>
            )}
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );

  return (
    <AdminLayout>
      {renderMemberList()}
      {renderUserForm()}
    </AdminLayout>
  );
};
