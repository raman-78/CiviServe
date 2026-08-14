import { MapPin, Navigation } from "lucide-react";
import type { ServiceCenter, CenterType } from "@/types";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatDistanceKm } from "@/lib/formatters";
import { toLabel } from "@/lib/utils";

const CENTER_TYPE_LABELS: Record<CenterType, string> = {
  csc: "CSC",
  esevai: "E-Sevai",
  "seva-kendra": "Seva Kendra",
  tehsil: "Tehsil",
  post_office: "Post Office",
  bank: "Bank",
};

interface CenterCardProps {
  center: ServiceCenter;
  onDirections?: (center: ServiceCenter) => void;
}

export function CenterCard({ center, onDirections }: CenterCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <Badge variant="secondary">{CENTER_TYPE_LABELS[center.type] ?? toLabel(center.type)}</Badge>
          {center.distanceKm !== undefined ? (
            <span className="text-xs font-medium text-primary">
              {formatDistanceKm(center.distanceKm)}
            </span>
          ) : null}
        </div>
        <CardTitle className="text-base">{center.name}</CardTitle>
        <CardDescription className="flex items-start gap-1">
          <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {center.address}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {center.timings ? (
          <p className="text-xs text-muted-foreground">{center.timings}</p>
        ) : null}
        {center.phone ? (
          <p className="text-xs">
            <a href={`tel:${center.phone}`} className="text-primary hover:underline">
              {center.phone}
            </a>
          </p>
        ) : null}
        {center.services.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {center.services.map((service) => (
              <Badge key={service} variant="outline">
                {service}
              </Badge>
            ))}
          </div>
        ) : null}
        {onDirections ? (
          <div className="pt-1">
            <button
              type="button"
              onClick={() => onDirections(center)}
              className="text-sm font-medium text-primary hover:underline"
            >
              <Navigation className="mr-1 inline h-4 w-4" />
              {center.distanceKm !== undefined ? "Get directions" : "Locate on map"}
            </button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
