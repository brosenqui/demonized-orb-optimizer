import * as React from "react";
import { Button } from "../ui/button";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "../ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "../ui/command";
import { Checkbox } from "../ui/checkbox";

const CATEGORIES = ["Soul", "Wings", "Ego", "Beast", "Wagon"] as const;

type Props = {
  value: string[];                // current shareable categories
  onChange: (next: string[]) => void;
};

export default function ShareablePicker({ value, onChange }: Props) {
  const [open, setOpen] = React.useState(false);

  function toggle(cat: string) {
    const set = new Set(value);
    if (set.has(cat)) set.delete(cat);
    else set.add(cat);
    onChange(Array.from(set));
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline">
          Shareable: {value.length > 0 ? value.join(", ") : "None"}
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
                    <Checkbox checked={checked} onCheckedChange={() => toggle(cat)} />
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
