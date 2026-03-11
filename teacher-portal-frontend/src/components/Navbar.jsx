import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/scenarios", label: "Scenarios" },
  { to: "/scenarios/create", label: "Create" },
  { to: "/sessions/start", label: "Start Session" },
  { to: "/guidelines/upload", label: "Guidelines" },
];

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-brand">
        <strong>Teacher Portal</strong>
        <span>VR Nursing Wound Care Simulation</span>
      </div>
      <nav className="navbar-links">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            end={item.end}
            to={item.to}
            className={({ isActive }) =>
              `nav-link${isActive ? " active" : ""}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
