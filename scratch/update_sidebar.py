with open('src/components/layout/AppSidebar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

target = """  const patientSections: SidebarSection[] = [
    {
      title: "Claim Operations",
      items: [
        { label: "My Claims", href: "/claims", icon: ZapIcon, highlight: true },
        { label: "Add Claim", href: "/claims/new", icon: Plus, isAction: true },
        { label: "Documents", href: "/documents", icon: FileText },
      ],
    },"""

replacement = """  const patientSections: SidebarSection[] = [
    {
      title: "Claim Operations",
      items: [
        { label: "Pre-Authorization", href: "/claims/new", icon: ClipboardList },
        { label: "My Claims", href: "/claims", icon: ZapIcon, highlight: true },
        { label: "Add Claim", href: "/claims/new", icon: Plus, isAction: true },
        { label: "Documents", href: "/documents", icon: FileText },
      ],
    },"""

admin_target = """  const sections: SidebarSection[] =
    sidebarRole === "admin"
      ? adminSections
      : sidebarRole === "claim_officer"
      ? tpaSections
      : sidebarRole === "hospital_coordinator"
      ? hospitalSections
      : patientSections;"""

admin_replacement = """  const sections: SidebarSection[] =
    sidebarRole === "claim_officer"
      ? tpaSections
      : sidebarRole === "hospital_coordinator"
      ? hospitalSections
      : patientSections;"""

assert target in text, "Target not found in AppSidebar.tsx"
text = text.replace(target, replacement)
if admin_target in text:
    text = text.replace(admin_target, admin_replacement)

with open('src/components/layout/AppSidebar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print("AppSidebar.tsx successfully updated!")
