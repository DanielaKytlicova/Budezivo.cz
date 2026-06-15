import React from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { Checkbox } from '../ui/checkbox';
import { Plus, Trash2, Info, User, ShieldAlert, Users } from 'lucide-react';

export const ProgramCollisionTab = ({
  formData,
  setFormData,
  programs,
  editingProgram,
  rooms,
  newRoomName,
  setNewRoomName,
  newRoomCapacity,
  setNewRoomCapacity,
  createRoom,
  deleteRoom,
  teamMembers = [],
}) => {
  const toggleCollisionResource = (resource) => {
    setFormData(prev => ({
      ...prev,
      collision_resources: prev.collision_resources.includes(resource)
        ? prev.collision_resources.filter(r => r !== resource)
        : [...prev.collision_resources, resource]
    }));
  };

  const toggleBlockedProgram = (programId) => {
    setFormData(prev => ({
      ...prev,
      blocked_program_ids: prev.blocked_program_ids.includes(programId)
        ? prev.blocked_program_ids.filter(id => id !== programId)
        : [...prev.blocked_program_ids, programId]
    }));
  };

  const toggleCollisionLecturer = (lecturerId) => {
    setFormData(prev => {
      const currentIds = prev.collision_lecturer_ids || [];
      return {
        ...prev,
        collision_lecturer_ids: currentIds.includes(lecturerId)
          ? currentIds.filter(id => id !== lecturerId)
          : [...currentIds, lecturerId]
      };
    });
  };

  const otherPrograms = programs.filter(p =>
    p.id !== editingProgram?.id && p.status !== 'archived'
  );

  const lecturerRoles = ['lektor', 'edukator', 'admin', 'spravce'];
  const lecturerMembers = teamMembers.filter(m =>
    lecturerRoles.includes(m.role) && m.status === 'active'
  );

  return (
    <div className="space-y-6">
      {/* Současně s jinými programy */}
      <Card className="p-4 md:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-slate-900">Současně s jinými programy</h3>
            <p className="text-sm text-gray-500 mt-1">
              Určuje, zda tento program může probíhat zároveň s jinými programy ve stejném čase.
            </p>
          </div>
          <div className="relative group ml-4">
            <Info className="w-4 h-4 text-gray-400 cursor-help" />
            <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              Pokud zvolíte „Pouze samostatně", tento program si vyhradí celý časový slot a ve stejnou dobu nelze rezervovat žádný jiný program.
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
          <div>
            <p className="font-medium text-slate-900 text-sm">
              {!formData.allow_parallel
                ? 'Pouze samostatně'
                : 'Ano — může probíhat současně s jinými'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {!formData.allow_parallel
                ? 'V době konání nemohou probíhat jiné programy.'
                : 'Další programy se mohou v tomto čase konat, s dále uvedenými omezeními.'}
            </p>
          </div>
          <Switch
            checked={formData.allow_parallel}
            onCheckedChange={(checked) => setFormData(prev => ({ ...prev, allow_parallel: checked }))}
            data-testid="collision-allow-parallel-toggle"
          />
        </div>
      </Card>

      {/* Počet potřebných lektorů */}
      <Card className="p-4 md:p-6 space-y-4" data-testid="program-required-lecturers-card">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-slate-900">Počet potřebných lektorů</h3>
            <p className="text-sm text-gray-500 mt-1">
              Kolik lektorů musí být v daný čas volných, aby šlo program rezervovat. Výchozí hodnota 1 = program se chová jako dosud.
            </p>
          </div>
          <Users className="w-5 h-5 text-[#4A6FA5] ml-4 shrink-0" />
        </div>

        <div className="flex items-center gap-3">
          <Input
            type="number"
            min={1}
            className="w-28"
            value={formData.required_lecturers ?? 1}
            onChange={(e) => setFormData(prev => ({
              ...prev,
              required_lecturers: Math.max(1, parseInt(e.target.value || '1', 10) || 1),
            }))}
            data-testid="program-required-lecturers-input"
          />
          <span className="text-sm text-gray-500">
            {(formData.required_lecturers ?? 1) === 1 ? 'lektor' : 'lektoři/ů'}
          </span>
        </div>

        {(formData.required_lecturers ?? 1) > 1 && (
          <div className="p-3 bg-[#4A6FA5]/10 border border-[#4A6FA5]/20 rounded-lg" data-testid="required-lecturers-info">
            <p className="text-xs text-[#4A6FA5]">
              Program půjde rezervovat jen pokud bude v daný čas volných alespoň <strong>{formData.required_lecturers}</strong> kvalifikovaných lektorů (těch, kteří mají tento program nastudovaný).
            </p>
          </div>
        )}
      </Card>

      {formData.allow_parallel && (
        <>
          {/* Ovlivněné zdroje */}
          <Card className="p-4 md:p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">Ovlivněné zdroje</h3>
              <div className="relative group">
                <Info className="w-4 h-4 text-gray-400 cursor-help" />
                <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  Zaškrtněte zdroje, u kterých chcete kontrolovat kolize.
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-500">
              Vyberte, které zdroje chcete kontrolovat při překryvu s jinými programy.
            </p>

            <div className="space-y-3">
              <label
                className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                  formData.collision_resources.includes('lecturer')
                    ? 'border-[#4A6FA5] bg-[#4A6FA5]/5'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                data-testid="collision-resource-lecturer"
              >
                <Checkbox
                  checked={formData.collision_resources.includes('lecturer')}
                  onCheckedChange={() => toggleCollisionResource('lecturer')}
                />
                <User className="w-5 h-5 text-[#4A6FA5]" />
                <div className="flex-1">
                  <p className="font-medium text-slate-900 text-sm">Lektor</p>
                  <p className="text-xs text-gray-500">
                    Kontrola, zda stejný lektor není přiřazen k překrývající se rezervaci
                  </p>
                </div>
              </label>

              {/* Výběr konkrétních lektorů */}
              {formData.collision_resources.includes('lecturer') && (
                <div className="ml-4 space-y-3 pl-4 border-l-2 border-[#4A6FA5]/30">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-[#4A6FA5]" />
                    <Label className="text-sm font-medium text-slate-700">Kontrolovat lektory</Label>
                  </div>
                  <p className="text-xs text-gray-500">
                    Vyberte konkrétní lektory, u kterých se bude kontrolovat kolize. Pokud nevyberete žádného, kontrolují se všichni lektoři s definovaným rozvrhem.
                  </p>

                  {lecturerMembers.length > 0 ? (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {lecturerMembers.map(member => {
                        const isSelected = (formData.collision_lecturer_ids || []).includes(member.id);
                        return (
                          <label
                            key={member.id}
                            className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                              isSelected
                                ? 'border-[#4A6FA5] bg-[#4A6FA5]/5'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                            data-testid={`collision-lecturer-${member.id}`}
                          >
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleCollisionLecturer(member.id)}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 text-sm truncate">
                                {member.first_name} {member.last_name}
                              </p>
                              <p className="text-xs text-gray-500">{member.email}</p>
                            </div>
                            <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                              {member.role}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <p className="text-sm text-gray-500">Žádní lektoři v týmu. Přidejte členy týmu v sekci Tým.</p>
                    </div>
                  )}

                  {(formData.collision_lecturer_ids || []).length > 0 && (
                    <div className="p-2 bg-[#4A6FA5]/10 border border-[#4A6FA5]/20 rounded-lg">
                      <p className="text-xs text-[#4A6FA5]">
                        Kontrola kolize pro {(formData.collision_lecturer_ids || []).length} {(formData.collision_lecturer_ids || []).length === 1 ? 'lektora' : 'lektorů'}
                      </p>
                    </div>
                  )}

                  {(formData.collision_lecturer_ids || []).length === 0 && lecturerMembers.length > 0 && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-xs text-amber-700">
                        Není vybrán žádný lektor — kontrolují se všichni lektoři s definovaným rozvrhem.
                      </p>
                    </div>
                  )}
                </div>
              )}

              <label
                className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                  formData.collision_resources.includes('room')
                    ? 'border-[#4A6FA5] bg-[#4A6FA5]/5'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                data-testid="collision-resource-room"
              >
                <Checkbox
                  checked={formData.collision_resources.includes('room')}
                  onCheckedChange={() => toggleCollisionResource('room')}
                />
                <ShieldAlert className="w-5 h-5 text-[#C4AB86]" />
                <div className="flex-1">
                  <p className="font-medium text-slate-900 text-sm">Místnost</p>
                  <p className="text-xs text-gray-500">
                    Kontrola, zda není překryv s jinou rezervací ve stejné místnosti
                  </p>
                </div>
              </label>
            </div>

            {formData.collision_resources.length === 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-700">
                  Žádný zdroj není vybrán — program se může překrývat se vším bez omezení.
                </p>
              </div>
            )}

            {/* Přiřazení místnosti */}
            {formData.collision_resources.includes('room') && (
              <div className="space-y-3 pt-3 border-t">
                <Label className="text-sm font-medium text-slate-700">Přiřazená místnost</Label>
                <Select
                  value={formData.room_id || 'none'}
                  onValueChange={(val) => setFormData(prev => ({ ...prev, room_id: val === 'none' ? null : val }))}
                >
                  <SelectTrigger data-testid="room-select">
                    <SelectValue placeholder="Vyberte místnost..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Žádná místnost</SelectItem>
                    {rooms.filter(r => r.is_active).map(room => (
                      <SelectItem key={room.id} value={room.id}>
                        {room.name}{room.capacity ? ` (${room.capacity} míst)` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {rooms.length === 0 && (
                  <p className="text-xs text-gray-500">Zatím nemáte žádné místnosti. Vytvořte je níže.</p>
                )}

                <div className="flex gap-2 items-end">
                  <div className="flex-1">
                    <Input
                      placeholder="Název místnosti..."
                      value={newRoomName}
                      onChange={(e) => setNewRoomName(e.target.value)}
                      className="text-sm"
                      data-testid="new-room-name"
                    />
                  </div>
                  <div className="w-24">
                    <Input
                      placeholder="Kapacita"
                      type="number"
                      value={newRoomCapacity}
                      onChange={(e) => setNewRoomCapacity(e.target.value)}
                      className="text-sm"
                      data-testid="new-room-capacity"
                    />
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    onClick={createRoom}
                    disabled={!newRoomName.trim()}
                    data-testid="create-room-btn"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>

                {rooms.length > 0 && (
                  <div className="space-y-1">
                    {rooms.map(room => (
                      <div key={room.id} className="flex items-center justify-between text-xs text-gray-600 px-2 py-1 bg-gray-50 rounded">
                        <span>{room.name}{room.capacity ? ` · ${room.capacity} míst` : ''}</span>
                        <button
                          type="button"
                          onClick={() => deleteRoom(room.id)}
                          className="text-red-400 hover:text-red-600"
                          data-testid={`delete-room-${room.id}`}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* Ruční omezení mezi programy */}
          <Card className="p-4 md:p-6 space-y-4" data-testid="collision-block-program-list">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">Ruční omezení mezi programy</h3>
              <div className="relative group">
                <Info className="w-4 h-4 text-gray-400 cursor-help" />
                <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  Vyberte programy, které se nesmí časově překrývat s tímto programem.
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-500">Nesmí se překrývat s těmito programy:</p>

            {otherPrograms.length > 0 ? (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {otherPrograms.map(prog => {
                  const isBlocked = formData.blocked_program_ids.includes(prog.id);
                  return (
                    <label
                      key={prog.id}
                      className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                        isBlocked ? 'border-red-300 bg-red-50' : 'border-gray-200 hover:border-gray-300'
                      }`}
                      data-testid={`collision-block-program-${prog.id}`}
                    >
                      <Checkbox
                        checked={isBlocked}
                        onCheckedChange={() => toggleBlockedProgram(prog.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 text-sm truncate">{prog.name_cs}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`px-1.5 py-0.5 text-xs rounded ${
                            prog.status === 'active' ? 'bg-slate-800 text-white' : 'bg-gray-200 text-gray-600'
                          }`}>
                            {prog.status === 'active' ? 'aktivní' : 'koncept'}
                          </span>
                          <span className="text-xs text-gray-400">{prog.duration} min</span>
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            ) : (
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">Žádné další programy k dispozici.</p>
              </div>
            )}

            {formData.blocked_program_ids.length > 0 && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">
                  <strong>{formData.blocked_program_ids.length}</strong> {formData.blocked_program_ids.length === 1 ? 'program' : 'programů'} nesmí běžet současně s tímto programem.
                </p>
              </div>
            )}
          </Card>
        </>
      )}

      {/* Shrnutí */}
      <Card className="p-4 md:p-6 bg-slate-50 border-slate-200">
        <h3 className="font-semibold text-slate-900 mb-3">Shrnutí nastavení</h3>
        <div className="space-y-2 text-sm">
          {!formData.allow_parallel ? (
            <p className="text-slate-700">
              Tento program probíhá <strong>pouze samostatně</strong> — v době jeho konání nemohou probíhat jiné programy.
            </p>
          ) : (
            <>
              <p className="text-slate-700">Tento program <strong>může probíhat současně</strong> s jinými programy.</p>
              {formData.collision_resources.length > 0 && (
                <p className="text-slate-600">
                  Kontrola kolizí: {formData.collision_resources.map(r =>
                    r === 'lecturer' ? 'Lektor' : 'Místnost'
                  ).join(', ')}
                </p>
              )}
              {formData.collision_resources.includes('lecturer') && (formData.collision_lecturer_ids || []).length > 0 && (
                <p className="text-slate-600">
                  Kontrolovaní lektoři: {(formData.collision_lecturer_ids || []).length}
                </p>
              )}
              {formData.blocked_program_ids.length > 0 && (
                <p className="text-slate-600">
                  Ručně blokované programy: {formData.blocked_program_ids.length}
                </p>
              )}
              {formData.collision_resources.length === 0 && formData.blocked_program_ids.length === 0 && (
                <p className="text-amber-600">
                  Bez omezení — program se může překrývat se vším.
                </p>
              )}
            </>
          )}
        </div>
      </Card>
    </div>
  );
};
