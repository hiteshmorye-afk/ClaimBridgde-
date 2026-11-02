import React, { useState, useEffect } from "react";
import {
  Users,
  ShieldCheck,
  UserPlus,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Building2,
  Mail,
  Copy,
  Check,
  RefreshCw,
  Clock,
  MoreVertical,
  Plus,
  Key,
} from "lucide-react";
import {
  fetchAdminUsers,
  updateAdminUserStatus,
  updateAdminUserRole,
  createAdminInvitation,
  fetchAdminOrganizations,
  createAdminOrganization,
  AdminUserRecord,
  OrganizationRecord,
} from "@/api/auth";
import { toast } from "sonner";

export function AdminUserManagement() {
  const [activeTab, setActiveTab] = useState<"users" | "organizations">("users");
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [organizations, setOrganizations] = useState<OrganizationRecord[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  // Invite Modal
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("hospital_coordinator");
  const [inviteOrg, setInviteOrg] = useState("");
  const [isInviting, setIsInviting] = useState(false);
  const [generatedInvite, setGeneratedInvite] = useState<{
    token: string;
    expires_at: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // New Org Modal
  const [isOrgModalOpen, setIsOrgModalOpen] = useState(false);
  const [orgName, setOrgName] = useState("");
  const [orgType, setOrgType] = useState<"hospital" | "tpa">("hospital");
  const [orgRegId, setOrgRegId] = useState("");
  const [orgEmail, setOrgEmail] = useState("");
  const [isCreatingOrg, setIsCreatingOrg] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [uList, oList] = await Promise.all([
        fetchAdminUsers({
          search: search || undefined,
          role: roleFilter !== "all" ? roleFilter : undefined,
          status: statusFilter !== "all" ? statusFilter : undefined,
        }),
        fetchAdminOrganizations(),
      ]);
      setUsers(uList);
      setOrganizations(oList);
    } catch (err: any) {
      toast.error(err?.message || "Failed to load administration data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [search, roleFilter, statusFilter]);

  const handleStatusChange = async (userId: string, newStatus: "active" | "suspended" | "deactivated") => {
    try {
      await updateAdminUserStatus(userId, newStatus);
      toast.success(`User status updated to ${newStatus}`);
      loadData();
    } catch (err: any) {
      toast.error(err?.message || "Status update failed");
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail || !inviteOrg) {
      toast.error("Please fill in email and organization name.");
      return;
    }
    setIsInviting(true);
    try {
      const res = await createAdminInvitation({
        email: inviteEmail,
        role: inviteRole,
        organization_name: inviteOrg,
      });
      setGeneratedInvite({
        token: res.invitation_token,
        expires_at: res.expires_at,
      });
      toast.success("Invitation generated successfully!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to generate invitation");
    } finally {
      setIsInviting(false);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName) {
      toast.error("Organization name is required.");
      return;
    }
    setIsCreatingOrg(true);
    try {
      await createAdminOrganization({
        name: orgName,
        org_type: orgType,
        registration_identifier: orgRegId || undefined,
        contact_email: orgEmail || undefined,
      });
      toast.success(`Organization "${orgName}" registered successfully.`);
      setIsOrgModalOpen(false);
      setOrgName("");
      setOrgRegId("");
      setOrgEmail("");
      loadData();
    } catch (err: any) {
      toast.error(err?.message || "Failed to create organization");
    } finally {
      setIsCreatingOrg(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Invitation link copied to clipboard!");
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Tab Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-5 rounded-2xl bg-card border border-border shadow-sm">
        <div>
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-primary" />
            System User & Organization Governance
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Role assignments, employee onboarding invitations, and account activation controls.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setGeneratedInvite(null);
              setInviteEmail("");
              setInviteOrg("");
              setIsInviteOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground font-semibold text-xs shadow-sm hover:bg-primary/90 transition"
          >
            <UserPlus className="w-4 h-4" />
            Invite Employee
          </button>
          <button
            type="button"
            onClick={() => setIsOrgModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-secondary text-secondary-foreground font-semibold text-xs border border-border hover:bg-secondary/80 transition"
          >
            <Building2 className="w-4 h-4" />
            Add Organization
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-2">
        <button
          type="button"
          onClick={() => setActiveTab("users")}
          className={`px-4 py-2 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
            activeTab === "users"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Users className="w-4 h-4" />
          Registered Users ({users.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("organizations")}
          className={`px-4 py-2 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
            activeTab === "organizations"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Registered Organizations ({organizations.length})
        </button>
      </div>

      {activeTab === "users" ? (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-2xl bg-card border border-border">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, email, organization..."
                className="w-full h-8 pl-9 pr-3 rounded-xl bg-secondary text-xs text-foreground outline-none border border-border focus:border-primary"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="h-8 rounded-xl bg-secondary border border-border px-2 text-foreground outline-none cursor-pointer"
              >
                <option value="all">All Roles</option>
                <option value="admin">Admin</option>
                <option value="hospital_coordinator">Hospital Coordinator</option>
                <option value="tpa_reviewer">TPA Reviewer</option>
                <option value="patient">Patient</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 rounded-xl bg-secondary border border-border px-2 text-foreground outline-none cursor-pointer"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="pending_email_verification">Pending Email</option>
                <option value="pending_tpa_provisioning">Pending Provisioning</option>
                <option value="suspended">Suspended</option>
              </select>
              <button
                type="button"
                onClick={loadData}
                className="p-1.5 rounded-lg border border-border hover:bg-secondary text-muted-foreground transition"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* User Table */}
          <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/40 border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
                  <tr>
                    <th className="py-3 px-4">User</th>
                    <th className="py-3 px-4">Role & Portal</th>
                    <th className="py-3 px-4">Organization & Details</th>
                    <th className="py-3 px-4">Account Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">
                        Loading users...
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">
                        No users match the selected filters.
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id} className="hover:bg-muted/30 transition">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-foreground">{u.full_name}</div>
                          <div className="text-[11px] text-muted-foreground">{u.email}</div>
                          {u.phone && <div className="text-[10px] text-muted-foreground/80">{u.phone}</div>}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              u.role === "admin"
                                ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                                : u.role === "tpa_reviewer" || u.role === "claims_officer"
                                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                                : u.role === "hospital_coordinator" || u.role === "claimant"
                                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                : "bg-slate-500/20 text-slate-400 border border-slate-500/30"
                            }`}
                          >
                            {u.role.replace("_", " ").toUpperCase()}
                          </span>
                          <div className="text-[10px] text-muted-foreground mt-0.5">Portal: {u.portal}</div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-foreground">{u.organization || "—"}</div>
                          {u.designation && (
                            <div className="text-[11px] text-muted-foreground">{u.designation}</div>
                          )}
                          {u.employee_id && (
                            <div className="text-[10px] font-mono text-muted-foreground/80">ID: {u.employee_id}</div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              u.account_status === "active" && u.is_active
                                ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30"
                                : u.account_status === "suspended" || !u.is_active
                                ? "bg-rose-500/10 text-rose-500 border border-rose-500/30"
                                : "bg-amber-500/10 text-amber-500 border border-amber-500/30"
                            }`}
                          >
                            {u.account_status === "active" && u.is_active ? (
                              <CheckCircle2 className="w-3 h-3" />
                            ) : (
                              <Clock className="w-3 h-3" />
                            )}
                            {u.is_active ? u.account_status.replace(/_/g, " ") : "Suspended"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {u.account_status !== "active" || !u.is_active ? (
                              <button
                                type="button"
                                onClick={() => handleStatusChange(u.id, "active")}
                                className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[11px] transition shadow-sm"
                              >
                                Activate
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => handleStatusChange(u.id, "suspended")}
                                className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 font-semibold text-[11px] transition"
                              >
                                Suspend
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Organizations Table */
        <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/40 border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
              <tr>
                <th className="py-3 px-4">Organization Name</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Registration ID</th>
                <th className="py-3 px-4">Contact</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {organizations.map((org) => (
                <tr key={org.id} className="hover:bg-muted/30 transition">
                  <td className="py-3 px-4 font-semibold text-foreground flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-primary" />
                    {org.name}
                  </td>
                  <td className="py-3 px-4">
                    <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-secondary text-foreground">
                      {org.org_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                    {org.registration_identifier || "—"}
                  </td>
                  <td className="py-3 px-4 text-muted-foreground">
                    {org.contact_email || org.contact_phone || "—"}
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-emerald-500 text-[10px] font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Active
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Invite Employee Modal */}
      {isInviteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-card rounded-2xl shadow-2xl max-w-md w-full border border-border p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h4 className="font-bold text-foreground flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-primary" />
                Invite Authorized Employee
              </h4>
              <button
                type="button"
                onClick={() => setIsInviteOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            {generatedInvite ? (
              <div className="space-y-4">
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1">
                    <CheckCircle2 className="w-4 h-4" /> Invitation Generated
                  </div>
                  Share this invitation token with <strong>{inviteEmail}</strong>. It expires in 7 days.
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Invitation Token</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={generatedInvite.token}
                      className="w-full h-9 px-3 rounded-xl bg-secondary font-mono text-xs text-foreground outline-none border border-border"
                    />
                    <button
                      type="button"
                      onClick={() => copyToClipboard(generatedInvite.token)}
                      className="p-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition shrink-0"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setIsInviteOpen(false)}
                    className="px-4 py-2 rounded-xl bg-secondary text-foreground text-xs font-semibold hover:bg-secondary/80 transition"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSendInvite} className="space-y-3 text-xs">
                <div>
                  <label className="font-semibold text-foreground">Employee Email</label>
                  <input
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="e.g. employee@starhealth.org"
                    className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                  />
                </div>

                <div>
                  <label className="font-semibold text-foreground">Assign Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                  >
                    <option value="hospital_coordinator">Hospital Coordinator</option>
                    <option value="tpa_reviewer">TPA Reviewer</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-foreground">Organization Name</label>
                  <input
                    type="text"
                    required
                    value={inviteOrg}
                    onChange={(e) => setInviteOrg(e.target.value)}
                    placeholder="e.g. Apollo Hospitals or Star Health TPA"
                    className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setIsInviteOpen(false)}
                    className="px-3.5 py-2 rounded-xl bg-secondary text-muted-foreground hover:text-foreground text-xs font-semibold transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isInviting}
                    className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-sm transition"
                  >
                    {isInviting ? "Generating..." : "Generate Invitation"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Add Organization Modal */}
      {isOrgModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-card rounded-2xl shadow-2xl max-w-md w-full border border-border p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h4 className="font-bold text-foreground flex items-center gap-2">
                <Building2 className="w-4 h-4 text-primary" />
                Register Healthcare Organization
              </h4>
              <button
                type="button"
                onClick={() => setIsOrgModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateOrg} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-foreground">Organization Name</label>
                <input
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="e.g. MAX Super Speciality Hospital"
                  className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                />
              </div>

              <div>
                <label className="font-semibold text-foreground">Organization Type</label>
                <select
                  value={orgType}
                  onChange={(e) => setOrgType(e.target.value as any)}
                  className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                >
                  <option value="hospital">Hospital / Healthcare Provider</option>
                  <option value="tpa">TPA / Health Insurer</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-foreground">Registration / License ID</label>
                <input
                  type="text"
                  value={orgRegId}
                  onChange={(e) => setOrgRegId(e.target.value)}
                  placeholder="e.g. HOSP-REG-8820 or IRDAI-TPA-019"
                  className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                />
              </div>

              <div>
                <label className="font-semibold text-foreground">Official Contact Email</label>
                <input
                  type="email"
                  value={orgEmail}
                  onChange={(e) => setOrgEmail(e.target.value)}
                  placeholder="e.g. contact@maxhealthcare.org"
                  className="mt-1 w-full h-9 px-3 rounded-xl bg-secondary text-foreground outline-none border border-border focus:border-primary"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsOrgModalOpen(false)}
                  className="px-3.5 py-2 rounded-xl bg-secondary text-muted-foreground hover:text-foreground text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingOrg}
                  className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-sm transition"
                >
                  {isCreatingOrg ? "Registering..." : "Register Organization"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
