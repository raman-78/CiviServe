import type { ServiceCenter } from "@/types";
import { CenterCard } from "@/features/centers/components/CenterCard";

interface CenterListProps {
  centers: ServiceCenter[];
  onDirections?: (center: ServiceCenter) => void;
}

/** List of nearby service centres. */
export function CenterList({ centers, onDirections }: CenterListProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {centers.map((center) => (
        <CenterCard key={center.id} center={center} onDirections={onDirections} />
      ))}
    </div>
  );
}