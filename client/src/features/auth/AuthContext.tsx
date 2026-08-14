/**
 * Firebase-backed auth state + session API.
 *
 * Subscribes to Firebase `onAuthStateChanged`, keeps a fresh ID token in the
 * token provider (`lib/auth-token.ts`) so `lib/api-client.ts` can attach it
 * automatically, and loads the server-side account (`/auth/me`) + profile.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  onAuthStateChanged,
  sendEmailVerification as firebaseSendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  updateProfile,
  type User,
} from "firebase/auth";
import type { CurrentUser, ProfileCompletion, UserProfile } from "@civiserve/shared";
import { get, post, del } from "@/lib/api-client";
import { setAuthToken } from "@/lib/auth-token";
import { isFirebaseConfigured } from "@/config/env";
import { getFirebaseAuth } from "@/lib/firebase";

interface AuthContextValue {
  /** Firebase user, null when signed out. */
  user: User | null;
  /** True until the initial auth state has been resolved. */
  initializing: boolean;
  /** Server-side account from /auth/me (null until loaded or for guests). */
  me: CurrentUser | null;
  /** Stored citizen profile (null until loaded). */
  profile: UserProfile | null;
  profileLoading: boolean;
  completion: ProfileCompletion | null;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  sendPasswordReset: (email: string) => Promise<void>;
  sendEmailVerification: () => Promise<void>;
  signOut: () => Promise<void>;
  revokeSessions: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  setProfile: (profile: UserProfile | null) => void;
  setCompletion: (completion: ProfileCompletion | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [completion, setCompletion] = useState<ProfileCompletion | null>(null);

  const loadMe = useCallback(async () => {
    try {
      const { data } = await get<CurrentUser>("/auth/me");
      setMe(data);
    } catch {
      setMe(null);
    }
  }, []);

  const loadProfile = useCallback(async () => {
    setProfileLoading(true);
    try {
      const { data: profileData } = await get<UserProfile>("/users/me/profile");
      const { data: completionData } = await get<ProfileCompletion>(
        "/users/me/profile/completion",
      );
      setProfile(profileData);
      setCompletion(completionData);
    } catch {
      setProfile(null);
      setCompletion(null);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isFirebaseConfigured) {
      setInitializing(false);
      return undefined;
    }

    const auth = getFirebaseAuth();
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      if (!firebaseUser) {
        setAuthToken(null);
        setMe(null);
        setProfile(null);
        setCompletion(null);
        setInitializing(false);
        return;
      }
      // Kick off token refresh + session hydration without blocking the UI.
      void (async () => {
        const token = await firebaseUser.getIdToken();
        setAuthToken(token);
        await loadMe();
        await loadProfile();
      })().finally(() => setInitializing(false));
    });

    return unsubscribe;
  }, [loadMe, loadProfile]);

  const signIn = useCallback(async (email: string, password: string) => {
    await signInWithEmailAndPassword(getFirebaseAuth(), email, password);
  }, []);

  const signInWithGoogle = useCallback(async () => {
    const provider = new GoogleAuthProvider();
    await signInWithPopup(getFirebaseAuth(), provider);
  }, []);

  const signUp = useCallback(async (name: string, email: string, password: string) => {
    const credential = await createUserWithEmailAndPassword(getFirebaseAuth(), email, password);
    if (name.trim()) {
      await updateProfile(credential.user, { displayName: name.trim() });
    }
    await credential.user.reload();
  }, []);

  const sendPasswordReset = useCallback(async (email: string) => {
    await sendPasswordResetEmail(getFirebaseAuth(), email);
  }, []);

  const sendEmailVerification = useCallback(async () => {
    if (!user) throw new Error("Not signed in.");
    await firebaseSendEmailVerification(user);
  }, [user]);

  const signOut = useCallback(async () => {
    setAuthToken(null);
    setMe(null);
    setProfile(null);
    setCompletion(null);
    await firebaseSignOut(getFirebaseAuth());
  }, []);

  const revokeSessions = useCallback(async () => {
    await post("/auth/revoke");
    setAuthToken(null);
    setMe(null);
    setProfile(null);
    setCompletion(null);
    await firebaseSignOut(getFirebaseAuth());
  }, []);

  const deleteAccount = useCallback(async () => {
    await del("/users/me/profile");
    setProfile(null);
    setCompletion(null);
    if (user) {
      await user.delete();
    }
    setAuthToken(null);
    setMe(null);
    await firebaseSignOut(getFirebaseAuth());
  }, [user]);

  const refreshProfile = useCallback(async () => {
    await loadProfile();
  }, [loadProfile]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      initializing,
      me,
      profile,
      profileLoading,
      completion,
      signIn,
      signInWithGoogle,
      signUp,
      sendPasswordReset,
      sendEmailVerification,
      signOut,
      revokeSessions,
      deleteAccount,
      refreshProfile,
      setProfile,
      setCompletion,
    }),
    [
      user,
      initializing,
      me,
      profile,
      profileLoading,
      completion,
      signIn,
      signInWithGoogle,
      signUp,
      sendPasswordReset,
      sendEmailVerification,
      signOut,
      revokeSessions,
      deleteAccount,
      refreshProfile,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
