with open("src/routes/documents.tsx", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the table headers with the requested 6 columns: Document, Category, Linked Claim, Upload Date, Processing Status, Action
old_thead = """              <thead className="bg-slate-50 dark:bg-[#0E1420] text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-[#9CA3AF]">

                <tr className="border-b border-slate-200 dark:border-[#1F2937]">

                  <th className="px-6 py-3.5">
                    Document File
                  </th>

                  <th className="px-6 py-3.5">
                    Category
                  </th>

                  <th className="px-6 py-3.5">
                    Linked Claim
                  </th>

                  <th className="px-6 py-3.5">
                    OCR Accuracy
                  </th>

                  <th className="px-6 py-3.5">
                    File Size
                  </th>

                  <th className="px-6 py-3.5">
                    Status
                  </th>

                  <th className="px-6 py-3.5 text-right">
                    Actions
                  </th>

                </tr>

              </thead>"""

new_thead = """              <thead className="bg-slate-50 dark:bg-[#0E1420] text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-[#9CA3AF]">
                <tr className="border-b border-slate-200 dark:border-[#1F2937]">
                  <th className="px-6 py-3.5">Document</th>
                  <th className="px-6 py-3.5">Category</th>
                  <th className="px-6 py-3.5">Linked Claim</th>
                  <th className="px-6 py-3.5">Upload Date</th>
                  <th className="px-6 py-3.5">Processing Status</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>"""

assert old_thead in text, "old_thead not found in documents.tsx"
text = text.replace(old_thead, new_thead, 1)

# Update row columns to match the 6 columns and include "View Extracted Information →" button
old_row_cells = """                    <td className="px-6 py-4">
                      <span className="font-mono font-bold text-[#06B6D4]">
                        {doc.confidence}%
                      </span>
                    </td>

                    <td className="px-6 py-4 font-mono text-slate-500 dark:text-[#9CA3AF]">
                      {doc.size}
                    </td>

                    <td className="px-6 py-4">

                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${
                          doc.status === "Verified"
                            ? "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981]"
                            : "border-[#EF4444]/40 bg-[#EF4444]/10 text-[#EF4444]"
                        }`}
                      >
                        {doc.status}
                      </span>

                    </td>

                    <td className="px-6 py-4 text-right">

                      <div className="flex items-center justify-end gap-2">

                        <button
                          onClick={() => handleViewDocument(doc.id)}
                          className="rounded-lg border border-slate-200 dark:border-[#1F2937] p-2 text-slate-500 hover:text-[#3B82F6] transition"
                          title="Open document verification report"
                          disabled={detailLoading}
                        >
                          <Eye className="size-4" />
                        </button>

                        <button
                          onClick={() =>
                            toast.success(
                              `Downloading ${doc.name}`
                            )
                          }
                          className="rounded-lg border border-slate-200 dark:border-[#1F2937] p-2 text-slate-500 hover:text-[#10B981]"
                        >
                          <Download className="size-4" />
                        </button>

                      </div>

                    </td>"""

new_row_cells = """                    <td className="px-6 py-4 text-xs font-mono text-slate-600 dark:text-[#9CA3AF]">
                      {doc.date}
                    </td>

                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${
                          doc.status === "Verified"
                            ? "border-[#10B981]/40 bg-[#10B981]/10 text-[#10B981]"
                            : doc.status.includes("Incorrect")
                            ? "border-rose-500/40 bg-rose-500/10 text-rose-400"
                            : "border-amber-500/40 bg-amber-500/10 text-amber-300"
                        }`}
                      >
                        {doc.status}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleViewDocument(doc.id)}
                          className="inline-flex items-center gap-1.5 rounded-xl border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-bold text-blue-600 transition hover:bg-blue-500 hover:text-white dark:text-blue-400 dark:hover:bg-blue-600"
                          title="Open document extraction & verification report"
                          disabled={detailLoading}
                        >
                          <Eye className="size-3.5" />
                          <span>View Extracted Information &rarr;</span>
                        </button>

                        <button
                          onClick={() => {
                            window.open(`/documents/${doc.id}/file`, '_blank');
                            toast.success(`Opening ${doc.name}`);
                          }}
                          className="rounded-lg border border-slate-200 p-1.5 text-slate-500 transition hover:text-[#10B981] dark:border-[#1F2937]"
                          title="Download / View original"
                        >
                          <Download className="size-3.5" />
                        </button>
                      </div>
                    </td>"""

assert old_row_cells in text, "old_row_cells not found in documents.tsx"
text = text.replace(old_row_cells, new_row_cells, 1)

# Also update colSpan in loading & empty rows from 7 to 6
text = text.replace('colSpan={7}', 'colSpan={6}')

with open("src/routes/documents.tsx", "w", encoding="utf-8") as f:
    f.write(text)

print("src/routes/documents.tsx table updated successfully!")
