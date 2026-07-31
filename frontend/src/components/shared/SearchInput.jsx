import { Search } from "lucide-react";
import { Input } from "../ui/input";
import { cn } from "../../lib/utils";

export function SearchInput({ value, onChange, placeholder = "Search…", className }) {
  return (
    <div className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-8"
      />
    </div>
  );
}
