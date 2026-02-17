import React, { useEffect, useState, useContext } from 'react';
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
import { Plus, MoreVertical, Shield, User, Eye, Trash2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLES = [
  { 
    value: 'admin', 
    label: 'Administrátor', 
    description: 'Plný přístup ke všem funkcím',
    icon: Shield,
    color: 'bg-[#4A6FA5] text-white'
  },
  { 
    value: 'staff', 
    label: 'Zaměstnanec', 
    description: 'Správa programů, rezervací a škol',
    icon: User,
    color: 'bg-[#84A98C] text-white'
  },
  { 
    value: 'viewer', 
    label: 'Návštěvník', 
    description: 'Pouze prohlížení dat',
    icon: Eye,
    color: 'bg-gray-200 text-gray-700'
  },
];

export const TeamPage = () => {
  const { user } = useContext(AuthContext);
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [inviteData, setInviteData] = useState({
    email: '',
    role: 'staff',
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
        email: user?.email,
        role: user?.role || 'admin',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/team/invite`, inviteData);
      toast.success('Pozvánka byla odeslána');
      setShowInviteDialog(false);
      setInviteData({ email: '', role: 'staff' });
      fetchTeamMembers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nepodařilo se odeslat pozvánku');
    }
  };

  const handleRoleChange = async (memberId, newRole) => {
    try {
      await axios.patch(`${API}/team/${memberId}/role`, { role: newRole });
      toast.success('Role byla změněna');
      fetchTeamMembers();
    } catch (error) {
      toast.error('Nepodařilo se změnit roli');
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm('Opravdu chcete odebrat tohoto člena týmu?')) return;
    
    try {
      await axios.delete(`${API}/team/${memberId}`);
      toast.success('Člen byl odebrán z týmu');
      fetchTeamMembers();
    } catch (error) {
      toast.error('Nepodařilo se odebrat člena');
    }
  };

  const getRoleInfo = (roleValue) => {
    return ROLES.find(r => r.value === roleValue) || ROLES[2];
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900">Správa týmu</h1>
            <p className="text-gray-600 mt-1">Spravujte přístupy a role členů vašeho týmu</p>
          </div>
          
          <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
            <DialogTrigger asChild>
              <Button className="bg-[#4A6FA5] text-white hover:bg-[#3d5c89]" data-testid="invite-member-button">
                <Plus className="w-4 h-4 mr-2" />
                Pozvat člena
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Pozvat nového člena týmu</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleInvite} className="space-y-4" data-testid="invite-form">
                <div>
                  <Label htmlFor="email">E-mail</Label>
                  <Input
                    id="email"
                    type="email"
                    data-testid="invite-email-input"
                    value={inviteData.email}
                    onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                    placeholder="kolega@muzeum.cz"
                    required
                    className="mt-2"
                  />
                </div>
                <div>
                  <Label>Role</Label>
                  <Select
                    value={inviteData.role}
                    onValueChange={(value) => setInviteData({ ...inviteData, role: value })}
                  >
                    <SelectTrigger className="mt-2" data-testid="invite-role-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLES.map(role => (
                        <SelectItem key={role.value} value={role.value}>
                          <div className="flex items-center gap-2">
                            <role.icon className="w-4 h-4" />
                            <span>{role.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button 
                  type="submit" 
                  className="w-full bg-[#4A6FA5] text-white hover:bg-[#3d5c89]"
                  data-testid="invite-submit-button"
                >
                  Odeslat pozvánku
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Role descriptions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {ROLES.map(role => {
            const Icon = role.icon;
            return (
              <Card key={role.value} className="p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${role.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">{role.label}</h3>
                  </div>
                </div>
                <p className="text-sm text-gray-600">{role.description}</p>
                <div className="mt-3 text-xs text-gray-500">
                  {role.value === 'admin' && (
                    <ul className="space-y-1">
                      <li>• Správa týmu a rolí</li>
                      <li>• Nastavení instituce</li>
                      <li>• Všechny funkce</li>
                    </ul>
                  )}
                  {role.value === 'staff' && (
                    <ul className="space-y-1">
                      <li>• Správa programů</li>
                      <li>• Správa rezervací</li>
                      <li>• Správa škol</li>
                    </ul>
                  )}
                  {role.value === 'viewer' && (
                    <ul className="space-y-1">
                      <li>• Prohlížení programů</li>
                      <li>• Prohlížení rezervací</li>
                      <li>• Žádné úpravy</li>
                    </ul>
                  )}
                </div>
              </Card>
            );
          })}
        </div>

        {/* Team members list */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Členové týmu</h2>
          
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4A6FA5] mx-auto"></div>
            </div>
          ) : teamMembers.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Zatím nejsou žádní členové týmu</p>
          ) : (
            <div className="space-y-3">
              {teamMembers.map((member) => {
                const roleInfo = getRoleInfo(member.role);
                const Icon = roleInfo.icon;
                const isCurrentUser = member.id === user?.id;
                
                return (
                  <div 
                    key={member.id} 
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                    data-testid={`team-member-${member.id}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${roleInfo.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">
                          {member.email}
                          {isCurrentUser && <span className="text-xs text-gray-500 ml-2">(vy)</span>}
                        </p>
                        <p className="text-sm text-gray-500">{roleInfo.label}</p>
                      </div>
                    </div>
                    
                    {!isCurrentUser && user?.role === 'admin' && (
                      <div className="flex items-center gap-2">
                        <Select
                          value={member.role}
                          onValueChange={(value) => handleRoleChange(member.id, value)}
                        >
                          <SelectTrigger className="w-32" data-testid={`role-select-${member.id}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {ROLES.map(role => (
                              <SelectItem key={role.value} value={role.value}>
                                {role.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveMember(member.id)}
                          className="text-red-500 hover:text-red-600 hover:bg-red-50"
                          data-testid={`remove-member-${member.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </AdminLayout>
  );
};
