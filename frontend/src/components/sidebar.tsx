import React from 'react';
import type { ChatThread } from '@/lib/api';
import { Plus, LogOut, User, MessageSquare, MoreHorizontal, Pen, Trash2 } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuAction,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface SidebarProps {
  threads: ChatThread[];
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (id: string) => void;
  onRenameThread: (id: string, title: string) => void;
  userEmail: string | undefined;
  onSignOut: () => void;
}

/**
 * Group threads by date: Today, Previous 7 Days, Older.
 */
function groupThreadsByDate(threads: ChatThread[]) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekAgo = new Date(todayStart.getTime() - 7 * 24 * 60 * 60 * 1000);

  const groups: { label: string; threads: ChatThread[] }[] = [
    { label: 'Today', threads: [] },
    { label: 'Previous 7 days', threads: [] },
    { label: 'Older', threads: [] },
  ];

  for (const thread of threads) {
    const date = new Date(thread.updated_at || thread.created_at);
    if (date >= todayStart) {
      groups[0].threads.push(thread);
    } else if (date >= weekAgo) {
      groups[1].threads.push(thread);
    } else {
      groups[2].threads.push(thread);
    }
  }

  return groups.filter((g) => g.threads.length > 0);
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onRenameThread,
  userEmail,
  onSignOut,
}) => {
  const groups = groupThreadsByDate(threads);
  const { isMobile } = useSidebar();

  return (
    <ShadcnSidebar variant="sidebar">
      <SidebarHeader>
        <div className="flex h-14 items-center gap-3 px-3">
          {/* Logo Avatar — warm gradient ring */}
          <div className="relative shrink-0 h-8 w-8">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-amber-800/60 via-stone-800/80 to-stone-900 p-0.5 shadow-lg ring-1 ring-amber-700/30">
              <div className="h-full w-full rounded-[10px] bg-stone-950 flex items-center justify-center overflow-hidden">
                <img
                  src="/log.png"
                  alt="Document Copilot"
                  className="h-6 w-6 object-contain drop-shadow-sm"
                />
              </div>
            </div>
          </div>
          <span className="text-sm font-semibold text-foreground tracking-tight">
            Document Copilot
          </span>
        </div>
        <div className="px-2 pb-2">
          <Button
            variant="outline"
            onClick={onCreateThread}
            className="w-full justify-start gap-2 h-9 text-xs font-medium"
          >
            <Plus size={14} />
            New chat
          </Button>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {threads.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-muted-foreground h-40">
            <MessageSquare size={24} className="mb-2 opacity-20" />
            <p className="text-xs font-medium">No conversations</p>
          </div>
        ) : (
          groups.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel className="text-[10px] tracking-wider uppercase text-muted-foreground">
                {group.label}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.threads.map((thread) => (
                    <SidebarMenuItem key={thread.id}>
                      <SidebarMenuButton
                        isActive={activeThreadId === thread.id}
                        onClick={() => onSelectThread(thread.id)}
                        className="text-xs h-8"
                      >
                        <span>{thread.title || 'Untitled Chat'}</span>
                      </SidebarMenuButton>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <SidebarMenuAction showOnHover>
                            <MoreHorizontal />
                            <span className="sr-only">More</span>
                          </SidebarMenuAction>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          className="w-48 rounded-lg"
                          side={isMobile ? "bottom" : "right"}
                          align={isMobile ? "end" : "start"}
                        >
                          <DropdownMenuItem
                            onClick={() => {
                              const newTitle = window.prompt("Rename chat:", thread.title);
                              if (newTitle && newTitle.trim()) {
                                onRenameThread(thread.id, newTitle.trim());
                              }
                            }}
                          >
                            <Pen className="text-muted-foreground mr-2 h-4 w-4" />
                            <span>Rename</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => onDeleteThread(thread.id)}>
                            <Trash2 className="text-muted-foreground mr-2 h-4 w-4" />
                            <span>Delete</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <Avatar className="h-7 w-7 border border-border">
                    <AvatarFallback className="bg-muted text-muted-foreground text-xs">
                      <User size={14} />
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-xs leading-tight">
                    <span className="truncate font-semibold">{userEmail}</span>
                    <span className="truncate text-muted-foreground">Free Tier</span>
                  </div>
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="bottom"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuItem onClick={onSignOut} className="text-red-500 focus:bg-red-500/10 focus:text-red-500">
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </ShadcnSidebar>
  );
};
