/** Typed API access for profile endpoints (docs/architecture/04). */
import { del, get, put } from "@/lib/api-client";
import type { ProfileCompletion, ProfileUpdate, UserProfile } from "@schemesathi/shared";

export async function fetchProfile(): Promise<UserProfile> {
  return (await get<UserProfile>("/users/me/profile")).data;
}

export async function updateProfile(payload: ProfileUpdate): Promise<UserProfile> {
  return (await put<UserProfile>("/users/me/profile", payload)).data;
}

export async function deleteProfile(): Promise<void> {
  await del<void>("/users/me/profile");
}

export async function fetchProfileCompletion(): Promise<ProfileCompletion> {
  return (await get<ProfileCompletion>("/users/me/profile/completion")).data;
}
