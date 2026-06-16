import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, BookOpen, GraduationCap, Settings, User } from 'lucide-react';
import styles from './Shell.module.css';

interface ShellProps {
  children: React.ReactNode;
}

const Shell: React.FC<ShellProps> = ({ children }) => {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <GraduationCap size={32} color="var(--color-secondary)" />
          <span>AI University</span>
        </div>
        
        <nav className={styles.nav}>
          <NavLink to="/" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/chat" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            <MessageSquare size={20} />
            <span>Study Chat</span>
          </NavLink>
          <NavLink to="/revisions" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            <BookOpen size={20} />
            <span>Revisions</span>
          </NavLink>
        </nav>

        <div className={styles.userProfile}>
          <User size={20} />
          <span>Student Account</span>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.header}>
          <h1>Welcome back, Candidate</h1>
          <div className={styles.headerActions}>
            <Settings size={20} />
          </div>
        </header>
        <main className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
};

export default Shell;
