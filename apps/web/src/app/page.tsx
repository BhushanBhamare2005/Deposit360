"use client";

import { useEffect, useState } from "react";
import type { AuthResponse, User } from "@deposit360/shared";

import { AuthForm } from "@/components/auth-form";
import { Dashboard } from "@/components/dashboard";
import { RoleDashboard } from "@/components/role-dashboard";
import { api } from "@/lib/api";

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const savedToken = window.sessionStorage.getItem("deposit360_token");
    if (!savedToken) {
      queueMicrotask(() => setReady(true));
      return;
    }
    api
      .me(savedToken)
      .then((currentUser) => {
        setToken(savedToken);
        setUser(currentUser);
      })
      .catch(() => window.sessionStorage.removeItem("deposit360_token"))
      .finally(() => setReady(true));
  }, []);

  function onAuthenticated(response: AuthResponse) {
    window.sessionStorage.setItem("deposit360_token", response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  }

  function onSignOut() {
    window.sessionStorage.removeItem("deposit360_token");
    setToken(null);
    setUser(null);
  }

  function onInstitutionCreated(institutionId: string) {
    setUser((currentUser) =>
      currentUser ? { ...currentUser, institution_id: institutionId } : currentUser
    );
  }

  if (!ready) {
    return <main className="loading-screen">Loading Deposit360…</main>;
  }
  if (!token || !user) {
    return <AuthForm onAuthenticated={onAuthenticated} />;
  }
  if (!user.roles.some((role) => ["institution_applicant", "institution_user"].includes(role))) {
    return <RoleDashboard token={token} user={user} onSignOut={onSignOut} />;
  }
  return (
    <Dashboard
      token={token}
      user={user}
      onInstitutionCreated={onInstitutionCreated}
      onSignOut={onSignOut}
    />
  );
}