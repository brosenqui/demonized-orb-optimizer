import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Checkbox } from "@/components/ui/checkbox";
import { CATEGORIES } from "@/lib/categoryData";

type Props = {
  value: readonly string[];                // current shareable categories
  onChange: (next: string[]) => void;
};

export default function ShareablePicker({ value, onChange }: Props) {
  const [open, setOpen] = React.useState(false);

  const toggle = React.useCallback((cat: string) => {
    const set = new Set(value);
    if (set.has(cat)) set.delete(cat);
    else set.add(cat);
    const ordered = CATEGORIES.filter((category) => set.has(category));
    onChange(ordered);
  }, [onChange, value]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline">
          Shareable: {value.length > 0 ? `${value.length} selected` : "None"}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-64">
        <Command>
          <CommandInput placeholder="Filter categories..." />
          <CommandList>
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup heading="Categories">
              {CATEGORIES.map((cat) => {
                const checked = value.includes(cat);
                return (
                  <CommandItem
                    key={cat}
                    onSelect={() => toggle(cat)}
                    className="flex items-center justify-between"
                  >
                    <span>{cat}</span>
                    <Checkbox checked={checked} className="pointer-events-none" />
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
