# Stylo Module System

Every client site is built from Stylo modules installed additively.
**Stylo Core is always first.** All other modules can be added at any time — including
after the site is already live and in use.

---

## The 10 Stylo Modules

| Module | Apps Inside | Depends On | Purpose |
|---|---|---|---|
| **Stylo Core** | frappe, stylo_core | — | Base layer — required on every site |
| **Stylo BMS** | payments, erpnext, india_compliance | Core | Business Management — ERP + India GST. Includes Gantt charts. |
| **Stylo HR** | hrms | Core + BMS | HR & Payroll |
| **Stylo CRM** | crm | Core | Sales, leads, deals, field visits |
| **Stylo Brain** | brain | Core | AI assistant (configure API key via Brain Settings UI) |
| **Stylo Analytics** | insights | Core | BI dashboards, DuckDB query engine, self-serve reporting |
| **Stylo LMS** | lms | Core (+ payments auto-installed if missing) | Learning Management System |
| **Stylo Lending** | lending | Core + BMS | Loan & lending management |
| **Stylo Desk** | telephony, helpdesk | Core | Customer support & ticketing |
| **Stylo Reco** | mint | Core (BMS recommended) | Bank reconciliation + Document AI |

### Dependency Rules

| Module | Rule |
|---|---|
| Stylo HR | Requires **Stylo BMS** first (hrms needs erpnext) |
| Stylo Lending | Requires **Stylo BMS** first (lending needs erpnext) |
| Stylo LMS | Requires **payments** — auto-installed if BMS is not on the site |
| Stylo Desk | telephony installs before helpdesk (handled by apps.txt order) |
| Stylo Reco | No hard dependency; warns if BMS is not present |
| All others | Can be added in any order after Core |

### BMS internal install order (fixed)
`payments → erpnext → india_compliance`

### Gantt Charts
Gantt chart views are **built into Stylo BMS** (erpnext Project module). No separate module needed.

---

## Common Site Configurations

| Client Type | Modules to Install |
|---|---|
| Custom App / Low-code | `stylo_core` |
| Sales Team | `stylo_core` + `stylo_crm` |
| Support / Helpdesk | `stylo_core` + `stylo_desk` |
| E-Learning Platform | `stylo_core` + `stylo_lms` |
| Analytics / BI | `stylo_core` + `stylo_analytics` |
| ERP India | `stylo_core` + `stylo_bms` |
| ERP + HR | `stylo_core` + `stylo_bms` + `stylo_hr` |
| ERP + Lending | `stylo_core` + `stylo_bms` + `stylo_lending` |
| ERP + Bank Reco | `stylo_core` + `stylo_bms` + `stylo_reco` |
| ERP + CRM + AI | `stylo_core` + `stylo_bms` + `stylo_crm` + `stylo_brain` |
| Full Stack | `stylo_core` + `stylo_bms` + `stylo_hr` + `stylo_crm` + `stylo_brain` + `stylo_analytics` |

---

## Create a New Site

```bash
./stylo_modules/new_site.sh <sitename> <server> <module1> [module2] ...
```

**Servers:** `demo` (stylo@57.155.90.17) | `stangroup` (frappe@104.43.114.1)

```bash
# Framework only (custom app site like NHS)
./stylo_modules/new_site.sh nhs2.stylo.io demo stylo_core

# CRM site
./stylo_modules/new_site.sh sales.stylo.io demo stylo_core stylo_crm

# Full ERP with HR and AI
./stylo_modules/new_site.sh client.stylo.io demo stylo_core stylo_bms stylo_hr stylo_brain

# E-learning
./stylo_modules/new_site.sh learn.stylo.io demo stylo_core stylo_lms

# Everything
./stylo_modules/new_site.sh full.stylo.io demo stylo_core stylo_bms stylo_hr stylo_crm stylo_brain stylo_analytics stylo_desk stylo_lms stylo_lending stylo_reco
```

Script does automatically:
1. `bench new-site` with correct DB credentials
2. Installs all apps from each module in the correct order
3. Runs post-install per module (migrate, clear-cache, prereq checks)
4. Sets Stylo branding (app_name, favicon, workspace icons) via Core post-install
5. Restarts the web service

---

## Add a Module to an Existing Site (at any time)

```bash
./stylo_modules/add_module.sh <sitename> <server> <module>
```

```bash
# Client started with CRM, now wants ERP
./stylo_modules/add_module.sh client.stylo.io demo stylo_bms

# Add HR after BMS is installed
./stylo_modules/add_module.sh client.stylo.io demo stylo_hr

# Add AI assistant to any site
./stylo_modules/add_module.sh client.stylo.io demo stylo_brain

# Add helpdesk + telephony
./stylo_modules/add_module.sh client.stylo.io demo stylo_desk
```

Existing site data is never touched — modules only add new doctypes on top.

---

## Folder Structure

```
stylo_modules/
├── README.md                      ← this file
├── new_site.sh                    ← create site + install modules
├── add_module.sh                  ← add module to existing site
│
├── stylo_core/
│   ├── apps.txt                   ← frappe, stylo_core
│   └── post_install.sh            ← branding, favicon, workspace icons
│
├── stylo_bms/
│   ├── apps.txt                   ← payments, erpnext, india_compliance
│   └── post_install.sh            ← migrate, clear-cache
│
├── stylo_hr/
│   ├── apps.txt                   ← hrms
│   └── post_install.sh            ← BMS prereq check, migrate, clear-cache
│
├── stylo_crm/
│   ├── apps.txt                   ← crm
│   └── post_install.sh            ← migrate, clear-cache
│
├── stylo_brain/
│   ├── apps.txt                   ← brain
│   └── post_install.sh            ← migrate, clear-cache (AI config via UI)
│
├── stylo_analytics/
│   ├── apps.txt                   ← insights
│   └── post_install.sh            ← migrate, clear-cache
│
├── stylo_lms/
│   ├── apps.txt                   ← lms
│   └── post_install.sh            ← payments prereq check, migrate, clear-cache
│
├── stylo_lending/
│   ├── apps.txt                   ← lending
│   └── post_install.sh            ← BMS prereq check, migrate, clear-cache
│
├── stylo_desk/
│   ├── apps.txt                   ← telephony, helpdesk (order matters)
│   └── post_install.sh            ← migrate, clear-cache
│
└── stylo_reco/
    ├── apps.txt                   ← mint
    └── post_install.sh            ← BMS warning, migrate, clear-cache
```

---

## Server Credentials (both servers)

| | demo | stangroup |
|---|---|---|
| SSH | `stylo@57.155.90.17` | `frappe@104.43.114.1` |
| Bench root | `/home/stylo/stylo` | `/home/frappe/stylo` |
| Admin password | `stylo123Admin` | `stylo123Admin` |
| MySQL root | `stylo123Admin` | `stylo123Admin` |
| Web service | `stylo-web.service` | `stangroup-web` |
