import { ErrorState } from "@/components/shared/ErrorState";
import { useRouteError } from "react-router-dom";
import { errorMessage } from "@/lib/errors";

/** Route-level error boundary (docs/architecture/08 + 13). */
export function ErrorElement() {
  const error = useRouteError();

  return (
    <div className="container px-4 py-10">
      <ErrorState message={errorMessage(error)} />
    </div>
  );
}
