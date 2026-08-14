import type { ComponentType } from "react";
import type { ChatMessage } from "@/types";
import { TextBubble } from "@/features/chat/components/bubbles/TextBubble";
import { SchemeCardBubble } from "@/features/chat/components/bubbles/SchemeCardBubble";
import { SchemeListBubble } from "@/features/chat/components/bubbles/SchemeListBubble";
import { EligibilityResultBubble } from "@/features/chat/components/bubbles/EligibilityResultBubble";
import { DocumentListBubble } from "@/features/chat/components/bubbles/DocumentListBubble";
import { CenterListBubble } from "@/features/chat/components/bubbles/CenterListBubble";
import { ApplicationLinkBubble } from "@/features/chat/components/bubbles/ApplicationLinkBubble";
import { QuickReplies } from "@/features/chat/components/bubbles/QuickReplies";
import { ErrorBubble } from "@/features/chat/components/bubbles/ErrorBubble";

/**
 * Content-type → component registry (docs/architecture/07). Adding a new rich
 * card type is a single registration here, not a chain of conditionals.
 */
export const messageComponentRegistry: Record<
  ChatMessage["contentType"],
  ComponentType<{ message: ChatMessage }>
> = {
  text: TextBubble,
  "scheme-card": SchemeCardBubble,
  "scheme-list": SchemeListBubble,
  "eligibility-result": EligibilityResultBubble,
  "document-list": DocumentListBubble,
  "center-list": CenterListBubble,
  "location-card": TextBubble,
  "application-link": ApplicationLinkBubble,
  "quick-replies": QuickReplies,
  image: TextBubble,
  error: ErrorBubble,
};
