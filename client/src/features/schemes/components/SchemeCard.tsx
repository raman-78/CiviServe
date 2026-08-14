import { Link } from "react-router-dom";
import type { SchemeSummary } from "@/types";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toLabel } from "@/lib/utils";

interface SchemeCardProps {
  scheme: SchemeSummary;
}

/** Catalog card linking to the scheme detail page. */
export function SchemeCard({ scheme }: SchemeCardProps) {
  return (
    <Link to={`/schemes/${scheme.code}`} className="group block h-full">
      <Card className="h-full transition-colors group-hover:border-primary/50">
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <Badge variant="secondary">{toLabel(scheme.category)}</Badge>
            <span className="text-xs text-muted-foreground">{scheme.stateCode === "*" ? "Central" : scheme.stateCode}</span>
          </div>
          <CardTitle className="line-clamp-2 text-base">{scheme.name.en}</CardTitle>
        </CardHeader>
        <CardContent>
          <CardDescription className="line-clamp-2">{scheme.summary.en}</CardDescription>
        </CardContent>
      </Card>
    </Link>
  );
}
