import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { AnalysisTable } from "@/types/planner";

const number = new Intl.NumberFormat("en", { maximumFractionDigits: 3 });

export function AnalysisSummaryTable({ table }: { table: AnalysisTable }) {
  return (
    <div className="mt-5 max-h-96 overflow-auto rounded-xl border border-border">
      <Table className="text-base" aria-label="Analysis summary table">
        <caption className="p-3 text-left text-sm text-muted-foreground">
          {table.sampleSize} observations · {table.rows.length} groups
        </caption>
        <TableHeader>
          <TableRow>
            {table.columns.map((column) => <TableHead scope="col" className="whitespace-nowrap px-3" key={column}>{column.replaceAll("_", " ")}</TableHead>)}
            {table.groupSizes && <TableHead scope="col" className="px-3 text-right">Observations</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {table.rows.map((row, index) => (
            <TableRow key={index}>
              {row.map((value, column) => <TableCell className="whitespace-nowrap px-3 tabular-nums" key={column}>{format(value)}</TableCell>)}
              {table.groupSizes && <TableCell className="px-3 text-right tabular-nums">{table.groupSizes[index]}</TableCell>}
            </TableRow>
          ))}
          {table.rows.length === 0 && <TableRow><TableCell colSpan={table.columns.length + (table.groupSizes ? 1 : 0)}>No grouped results.</TableCell></TableRow>}
        </TableBody>
      </Table>
    </div>
  );
}

function format(value: AnalysisTable["rows"][number][number]): string {
  if (value === null) return "—";
  return typeof value === "number" ? number.format(value) : String(value);
}
