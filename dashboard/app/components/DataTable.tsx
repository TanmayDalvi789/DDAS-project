/**
 * DataTable Component
 * Reusable table for displaying rows with columns
 */

interface Column<T> {
  key: keyof T | string;
  label: string;
  render?: (value: any, row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: keyof T;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  rowKey,
}: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className="text-left px-4 py-2.5 font-semibold text-slate-700"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={String(row[rowKey])} className="table-row">
              {columns.map((col) => (
                <td key={String(col.key)} className="px-4 py-2.5 text-slate-900">
                  {col.render ? col.render(row[col.key as keyof T], row) : String(row[col.key as keyof T])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
