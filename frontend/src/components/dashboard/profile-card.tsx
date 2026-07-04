"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  MapPin,
  Building2,
  Link as LinkIcon,
  Users,
  BookOpen,
  GitFork,
} from "lucide-react";
import type { UserProfile } from "@/types";

interface ProfileCardProps {
  user: UserProfile | null;
  isLoading: boolean;
}

export function ProfileCard({ user, isLoading }: ProfileCardProps) {
  if (isLoading) {
    return (
      <Card className="border-border/50">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <Skeleton className="h-16 w-16 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!user) return null;

  return (
    <Card className="border-border/50 hover:border-primary/20 transition-colors">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Profile</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-start gap-4">
          <Avatar className="h-16 w-16 border-2 border-primary/20">
            <AvatarImage src={user.avatar_url} alt={user.name} />
            <AvatarFallback className="text-lg">
              {user.name?.charAt(0)?.toUpperCase() || user.username?.charAt(0)?.toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base truncate">{user.name || user.username}</h3>
            <p className="text-sm text-muted-foreground">@{user.username}</p>
            {user.bio && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{user.bio}</p>
            )}
          </div>
        </div>

        {/* Meta info */}
        <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {user.company && (
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              {user.company}
            </span>
          )}
          {user.location && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {user.location}
            </span>
          )}
          {user.blog && (
            <a
              href={user.blog.startsWith("http") ? user.blog : `https://${user.blog}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-primary transition-colors"
            >
              <LinkIcon className="h-3 w-3" />
              Website
            </a>
          )}
        </div>

        {/* Stats */}
        <div className="mt-4 grid grid-cols-3 gap-3 pt-3 border-t border-border/50">
          <div className="text-center">
            <p className="text-lg font-semibold">{user.public_repos}</p>
            <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
              <BookOpen className="h-3 w-3" />
              Repos
            </p>
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold">{user.followers}</p>
            <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
              <Users className="h-3 w-3" />
              Followers
            </p>
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold">{user.following}</p>
            <p className="text-xs text-muted-foreground flex items-center justify-center gap-1">
              <GitFork className="h-3 w-3" />
              Following
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
