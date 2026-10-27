// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

const STATS_TYPE_ORDER = ["functions", "lines", "regions", "branches"];
let function_report_state = { pending: 0, loaded: 0, errors: 0, functions: 0 };
const source_report_state = { lines: null, reports: new Map(), pending: new Set(), errors: new Set() };

function is_path_in_scope(path, file_path) {
    let directory = path.endsWith("/") ? path.slice(0, -1) : path;
    return path === "." || file_path === path || file_path.startsWith(`${directory}/`);
}

function append_platform_stats_row(stats_table, platform, file_platform_stats_covered, file_stats_count) {
    let stats_table_body = stats_table.getElementsByTagName("tbody")[0]
    let platform_row = stats_table_body.insertRow();
    let platform_name = platform_row.insertCell();
    platform_row.className = `${platform} row`;
    platform_name.innerHTML = platform;
    let platform_covered = platform_row.insertCell();
    platform_covered.innerHTML = file_platform_stats_covered;
    platform_covered.className = "covered";
    let platform_count = platform_row.insertCell();
    platform_count.innerHTML = file_stats_count;
    platform_count.className = "count";
    let platform_covered_percent = platform_row.insertCell();
    platform_covered_percent.innerHTML = `${Math.round(file_platform_stats_covered / file_stats_count * 100)}%`;
    platform_covered_percent.className = "covered_percent";
}

function update_platform_stats_row(total_row, file_platform_stats_covered, file_stats_count) {
    let total_covered_cell = total_row.getElementsByClassName("covered")[0];
    let prev_total_covered = parseInt(total_covered_cell.innerHTML);
    let new_covered = prev_total_covered + file_platform_stats_covered;
    total_covered_cell.innerHTML = new_covered;

    let total_count_cell = total_row.getElementsByClassName("count")[0];
    let prev_total_count = parseInt(total_count_cell.innerHTML);
    let new_count = prev_total_count + file_stats_count;
    total_count_cell.innerHTML = new_count;

    let total_covered_percent_cell = total_row.getElementsByClassName("covered_percent")[0];
    total_covered_percent_cell.innerHTML = `${Math.round(new_covered / new_count * 100)}%`;
}

function update_summary_file_stats_table(file_row, stats_type, platform, file_summary) {
    let stats_table = file_row.getElementsByClassName(`${stats_type} table`)[0];
    let file_platform_stats_covered = file_summary[stats_type]["covered"];
    let file_stats_count = file_summary[stats_type]["count"];

    // total row
    let total_row = stats_table.getElementsByClassName("total row")[0];
    if (total_row == undefined) {
        append_platform_stats_row(stats_table, "total", file_platform_stats_covered, file_stats_count);
    } else {
        update_platform_stats_row(total_row, file_platform_stats_covered, file_stats_count)
    }

    // platform row
    let platform_row = stats_table.getElementsByClassName(`${platform} row`)[0];
    if (platform_row == undefined) {
        append_platform_stats_row(stats_table, platform, file_platform_stats_covered, file_stats_count);
    } else {
        update_platform_stats_row(platform_row, file_platform_stats_covered, file_stats_count)
    }
}

function update_summary_table(path, platform, summary_data) {
    let summary_total_row = document.getElementById("Total");
    let card_totals = Object.fromEntries(STATS_TYPE_ORDER.map(stats_type => [stats_type, { covered: 0, count: 0 }]));
    for (let file of summary_data["data"][0]["files"]) {
        let file_name = `./${file["filename"]}`;
        if (!is_path_in_scope(path, file_name)) {
            continue
        }

        let file_summary = file["summary"];
        for (let stats_type of STATS_TYPE_ORDER) {
            if (stats_type in file_summary) {
                card_totals[stats_type].covered += file_summary[stats_type]["covered"];
                card_totals[stats_type].count += file_summary[stats_type]["count"];
            }
        }

        let path_parts = path.split("/");
        let file_path_parts = file_name.split("/").slice(0, path_parts.length + 1);
        let file_path = file_path_parts.join("/");
        let file_row = document.getElementById(file_path);
        if (file_row) {
            for (let stats_type of STATS_TYPE_ORDER) {
                if (stats_type in file_summary) {
                    update_summary_file_stats_table(summary_total_row, stats_type, platform, file_summary)
                    update_summary_file_stats_table(file_row, stats_type, platform, file_summary)
                }
            }
        }

    }
    update_coverage_cards(card_totals);
}

function update_coverage_cards(card_totals) {
    for (let [stats_type, totals] of Object.entries(card_totals)) {
        let card = document.querySelector(`.coverage-card[data-stat="${stats_type}"]`);
        if (!card) {
            continue;
        }

        let covered_cell = card.dataset.covered || 0;
        let count_cell = card.dataset.count || 0;
        let covered = Number(covered_cell) + totals.covered;
        let count = Number(count_cell) + totals.count;
        card.dataset.covered = covered;
        card.dataset.count = count;

        let value = card.querySelector(".card-value");
        let detail = card.querySelector(".card-detail");
        let progress = card.querySelector(".progress-value");
        if (count === 0) {
            value.textContent = "—";
            detail.textContent = "No coverage points";
            progress.style.width = "0%";
            card.removeAttribute("data-level");
            continue;
        }

        let percent = Math.round(covered / count * 100);
        value.textContent = `${percent}%`;
        detail.textContent = `${covered} of ${count} covered`;
        progress.style.width = `${percent}%`;
        card.dataset.level = percent < 60 ? "low" : "good";
    }
}

function update_file_details(path, platform, file_details) {
    if (!Array.isArray(file_details?.segments)) {
        throw new Error(`Missing coverage segments for ${path} (${platform})`);
    }
    source_report_state.reports.set(platform, file_details);
    source_report_state.pending.delete(platform);
    source_report_state.errors.delete(platform);

    let selector = document.getElementById("source_report");
    if (![...selector.options].some(option => option.value === platform)) {
        selector.add(new Option(platform, platform));
        selector.disabled = false;
    }
    render_source_coverage();
}

function source_column_offset(text, column) {
    let bytes = 1;
    let offset = 0;
    for (let character of text) {
        if (bytes >= column) {
            break;
        }
        bytes += new TextEncoder().encode(character).length;
        offset += character.length;
    }
    return offset;
}

function build_line_coverage(lines, segments) {
    let coverage = lines.map(() => ({ count: null, ranges: [] }));
    // Cobertura-derived reports use column zero for independent line hits.
    if (segments.every(segment => segment[1] === 0)) {
        for (let [line, , count, has_count] of segments) {
            if (coverage[line - 1] && has_count) {
                coverage[line - 1].count = count;
                coverage[line - 1].ranges = [{ start: 0, end: lines[line - 1].length, count }];
            }
        }
        return coverage;
    }

    let index = 0;
    let wrapped = null;
    for (let line = 1; line <= lines.length; line++) {
        let line_segments = [];
        while (index < segments.length && segments[index][0] === line) {
            line_segments.push(segments[index++]);
        }
        let entries = line_segments.filter(segment => segment[3] && segment[4] && !segment[5]);
        let first = line_segments[0];
        let skipped = first && !first[3] && first[4];
        let mapped = (!skipped && (wrapped?.[3] || entries.length > 0))
            || line_segments.some(segment => segment[3] && segment[4]);
        let stats = coverage[line - 1];
        if (mapped) {
            // LLVM uses the maximum region-entry/wrapped count, not their sum.
            stats.count = Math.max(wrapped?.[2] ?? 0, ...entries.map(segment => segment[2]));
        }

        let active = wrapped;
        let start = 0;
        for (let segment of line_segments) {
            let end = source_column_offset(lines[line - 1], segment[1]);
            if (active?.[3] && !active[5] && start < end) {
                stats.ranges.push({ start, end, count: active[2] });
            }
            active = segment;
            start = end;
        }
        if (active?.[3] && !active[5] && start < lines[line - 1].length) {
            stats.ranges.push({ start, end: lines[line - 1].length, count: active[2] });
        }
        if (line_segments.length) {
            wrapped = line_segments[line_segments.length - 1];
        }
    }
    return coverage;
}

function render_source_coverage() {
    if (!source_report_state.lines) {
        return;
    }
    let selected = document.getElementById("source_report").value;
    let reports = [...source_report_state.reports.entries()]
        .filter(([platform]) => selected === "" || platform === selected)
        .map(([, details]) => build_line_coverage(source_report_state.lines, details.segments));
    let body = document.getElementById("file_details_table_body");
    body.replaceChildren();
    source_report_state.lines.forEach((text, index) => {
        let row = body.insertRow();
        row.id = `L${index + 1}`;
        let anchor = document.createElement("a");
        anchor.href = `#${row.id}`;
        anchor.textContent = index + 1;
        row.insertCell().appendChild(anchor);

        let stats = reports.map(report => report[index]);
        let counts = stats.map(line => line.count).filter(count => count !== null);
        let count = counts.length ? counts.reduce((sum, value) => sum + value, 0) : null;
        let count_cell = row.insertCell();
        count_cell.className = count === null ? "skipped-line" : count > 0 ? "covered-line" : "uncovered-line";
        count_cell.textContent = count ?? "";
        count_cell.title = count === null ? "Not instrumented" : `${count} executions`;

        let source_cell = row.insertCell();
        let ranges = stats.flatMap(line => line.ranges);
        let boundaries = [...new Set([0, text.length, ...ranges.flatMap(range => [range.start, range.end])])]
            .sort((a, b) => a - b);
        for (let boundary = 0; boundary < boundaries.length - 1; boundary++) {
            let start = boundaries[boundary];
            let end = boundaries[boundary + 1];
            let covering = ranges.filter(range => range.start <= start && range.end >= end);
            let part = text.slice(start, end);
            if (covering.length && covering.every(range => range.count === 0)) {
                let span = document.createElement("span");
                span.className = "uncovered-region";
                span.title = "Uncovered region: 0 executions";
                span.textContent = part;
                source_cell.appendChild(span);
            } else {
                source_cell.appendChild(document.createTextNode(part));
            }
        }
    });
    document.getElementById("source_count_header").textContent = selected === "" && reports.length > 1
        ? "Count (sum)" : "Count";
    let status;
    if (selected !== "" && reports.length === 0) {
        status = source_report_state.pending.has(selected)
            ? `Coverage details for ${selected} are loading.`
            : `Coverage details for ${selected} are unavailable.`;
    } else if (reports.length === 0) {
        status = source_report_state.pending.size
            ? "Source text loaded; coverage details are loading."
            : "Source text loaded; coverage details are unavailable.";
    } else if (source_report_state.pending.size) {
        status = `${reports.length} loaded report(s); ${source_report_state.pending.size} report(s) still loading.`;
    } else if (source_report_state.errors.size) {
        status = `${reports.length} loaded report(s); coverage details unavailable for ${source_report_state.errors.size} report(s).`;
    } else {
        status = selected === "" && reports.length > 1
            ? `${reports.length} loaded reports summed. Select a report to compare with its LLVM HTML.`
            : "Line counts and uncovered regions for the selected report. Blank counts are not instrumented.";
    }
    document.getElementById("source_status").textContent = status;
    if (window.location.hash) {
        document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "nearest" });
    }
}


function handle_files_data (path, manifest_data, files_data) {
    source_report_state.pending = new Set(Object.keys(manifest_data));
    source_report_state.errors.clear();
    init_summary_table(path, manifest_data, files_data);
    init_function_table(Object.keys(manifest_data).length);
    
    let coverage_ul = document.getElementById("coverage_list");
    Object.entries(manifest_data).forEach(([platform, value]) => {
        console.debug(platform, value);
        let coverage_path = value["path"];
        let coverage_file = value["coverage_file"];
        let list_item = document.createElement("li");
        let anchor = document.createElement("a");
        anchor.href = coverage_path;
        anchor.innerHTML = platform;
        list_item.appendChild(anchor);
        coverage_ul.appendChild(list_item);

        fetch(`${coverage_path}/coverage_details.json`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(details_data => {
                add_function_rows(path, platform, details_data);
                complete_function_report();
            })
            .catch(error => {
                console.error(`Unable to load function details for ${platform}:`, error);
                function_report_state.errors += 1;
                complete_function_report();
            });

        fetch(`${coverage_path}/${coverage_file}`).then(response => response.json()).then(summary_data => {
            console.debug("Summary: ", summary_data);
            update_summary_table(path, platform, summary_data);
            if (document.getElementById("file_details_div").hidden) {
                console.debug("File details hidden");
            } else {
                fetch(`${coverage_path}/code_coverage_details/${path}.json`).then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                }).then(file_details => {
                    update_file_details(path, platform, file_details);
                }).catch(error => {
                    console.error(`Unable to load source coverage for ${platform}:`, error);
                    source_report_state.pending.delete(platform);
                    source_report_state.errors.add(platform);
                    let message = document.getElementById("source_error");
                    message.hidden = false;
                    message.textContent += ` Source coverage unavailable for ${platform}: ${error.message}.`;
                    render_source_coverage();
                });
            }
        }).catch(error => {
            console.error(`Unable to load coverage summary for ${platform}:`, error);
            source_report_state.pending.delete(platform);
            source_report_state.errors.add(platform);
            render_source_coverage();
        });
    });
}

function init_function_table(report_count) {
    document.getElementById("function_table_body").replaceChildren();
    function_report_state = { pending: report_count, loaded: 0, errors: 0, functions: 0 };
    document.getElementById("function_report_status").textContent = report_count
        ? "Loading function details…"
        : "No coverage reports were found.";
}

function add_function_rows(path, platform, details_data) {
    let function_table_body = document.getElementById("function_table_body");
    let functions = Array.isArray(details_data["data"])
        ? details_data["data"].flatMap(export_data => export_data["functions"] || [])
        : details_data["functions"];
    if (!Array.isArray(functions)) {
        return;
    }

    for (let covered_function of functions) {
        let filenames = Array.isArray(covered_function["filenames"])
            ? covered_function["filenames"]
            : [];
        let expanded_file_ids = new Set(covered_function["expandedFiles"] || []);
        let filename = filenames.find((_, file_id) => !expanded_file_ids.has(file_id));
        if (!filename) {
            continue;
        }
        let file_path = `./${filename.replace(/^\.?\//, "")}`;
        if (!is_path_in_scope(path, file_path)) {
            continue;
        }

        let is_covered = Number(covered_function["count"]) > 0;
        let row = function_table_body.insertRow();
        row.dataset.coverage = is_covered ? "covered" : "uncovered";

        let status_cell = row.insertCell();
        let status_badge = document.createElement("span");
        status_badge.className = `function-badge${is_covered ? "" : " uncovered"}`;
        status_badge.textContent = is_covered ? "Covered" : "Not covered";
        status_cell.appendChild(status_badge);

        let function_name_cell = row.insertCell();
        function_name_cell.textContent = covered_function["demangled_name"] || covered_function["name"] || "(unnamed function)";
        function_name_cell.title = covered_function["name"] || "";
        row.insertCell().textContent = filename;
        row.insertCell().textContent = covered_function["count"] ?? 0;
        row.insertCell().textContent = platform;
        function_report_state.functions += 1;
    }
}

function complete_function_report() {
    function_report_state.pending -= 1;
    function_report_state.loaded += 1;
    if (function_report_state.pending > 0) {
        return;
    }

    let status = document.getElementById("function_report_status");
    if (function_report_state.functions === 0) {
        status.textContent = function_report_state.errors
            ? `Function details could not be loaded for ${function_report_state.errors} report(s), or are not available for this coverage format.`
            : "No function-level coverage data is available for this report.";
        return;
    }

    let status_text = `${function_report_state.functions} function entr${function_report_state.functions === 1 ? "y" : "ies"} shown`;
    if (function_report_state.errors) {
        status_text += ` · function details unavailable for ${function_report_state.errors} report(s)`;
    }
    status.textContent = status_text;
    apply_function_filters();
}

function apply_function_filters() {
    let coverage_filter = document.getElementById("function_filter").value;
    let search_term = document.getElementById("function_search").value.toLowerCase();
    let visible_count = 0;
    for (let row of document.getElementById("function_table_body").rows) {
        if (row.id === "function_empty_row") {
            continue;
        }
        let matches_coverage = coverage_filter == "all" || row.dataset.coverage == coverage_filter;
        let matches_search = row.textContent.toLowerCase().includes(search_term);
        row.hidden = !matches_coverage || !matches_search;
        if (!row.hidden) {
            visible_count += 1;
        }
    }

    let empty_row = document.getElementById("function_empty_row");
    if (visible_count === 0 && function_report_state.functions > 0) {
        if (!empty_row) {
            empty_row = document.getElementById("function_table_body").insertRow();
            empty_row.id = "function_empty_row";
            let cell = empty_row.insertCell();
            cell.colSpan = 5;
            cell.className = "function-empty";
        }
        empty_row.cells[0].textContent = "No functions match these filters.";
        empty_row.hidden = false;
    } else if (empty_row) {
        empty_row.hidden = true;
    }
}


function handle_manifest(path, manifest_data) {
    fetch("data/files.json").then(response => response.json()).then(files_data => {
        console.debug("files_data: ", files_data);
        handle_files_data(path, manifest_data, files_data);
    });
}

function list_path(path, files) {
    let parts = path.split("/");
    for (let part of parts) {
        if (part in files) {
            // double click into folder
            files = files[part];
        } else {
            // check if this is a file
            console.assert(part in files["files"], `Path ${path} not found in manifest`);
            // return the file
            let file = {};
            file[part] = files["files"][part];
            return file;
        }
    }

    let folders = {};
    for (let folder in files) {
        if (folder != "files") {
            folders[folder] = `${path}/${folder}`;
        }
    }
    return Object.assign({}, folders, files["files"]);
}

function init_summary_cell(file_row, stats_type) {
    let function_cell = file_row.insertCell();
    let function_table = document.createElement("table");
    function_table.className = `${stats_type} table`;
    function_table.createTHead().insertRow().innerHTML = "<th>Platform</th><th>Covered</th><th>Count</th><th>Covered %</th>";
    function_table.createTBody();
    function_cell.appendChild(function_table);
}

function init_summary_row(summary_table, file_path) {
    let file_row = summary_table.insertRow();
    file_row.id = file_path;
    let file_path_cell = file_row.insertCell();

    if (file_path == "Total") {
        file_path_cell.innerHTML = file_path;
    } else {
        let anchor = document.createElement("a");
        anchor.href = `?path=${file_path}`;
        anchor.innerHTML = file_path;
        file_path_cell.appendChild(anchor);
    }

    for (let stats_type of STATS_TYPE_ORDER) {
        init_summary_cell(file_row, stats_type);
    }
}

function init_summary_table(path, manifest, files_data) {
    console.log("Updating summary table for path: ", path);
    let summary_table = document.getElementById("summary_table_body");
    let file_details_div = document.getElementById("file_details_div");
    init_summary_row(summary_table, "Total")
    let files = list_path(path, files_data);
    for (const [file_name, file_path] of Object.entries(files)) {
        init_summary_row(summary_table, file_path)
        if (path == file_path) {
            file_details_div.hidden = false;
            init_file_details_table_body(path, files_data.source_root ?? "../../../../")
        } else {
            file_details_div.hidden = true;
        }
    }
}

function init_parent_anchor(path) {
    let parent_anchor = document.getElementById("parent_anchor");
    let parent_path = path.split("/").slice(0, -1).join("/");
    if (parent_path) {
        parent_anchor.href = `?path=${parent_path}`;
        parent_anchor.textContent = `Go to parent .. (${parent_path})`;
    } else {
        parent_anchor.hidden = true;
    }
}

function init_file_details_table_body(path, source_root) {
    let file_details_table = document.getElementById("file_details_table");
    file_details_table.hidden = false;
    const source_url = new URL(path, new URL(source_root, window.location.href));
    fetch(source_url).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} loading ${source_url}`);
        }
        return response.text();
    }).then(file => {
        let lines = file.split(/\r\n|\n/);
        if (lines[lines.length - 1] === "") {
            lines.pop();
        }
        source_report_state.lines = lines;
        render_source_coverage();
    }).catch(error => {
        console.error("Unable to load source text:", error);
        document.getElementById("source_status").textContent = "Source text could not be loaded.";
        let message = document.getElementById("source_error");
        message.hidden = false;
        message.textContent += ` Source text unavailable: ${error.message}.`;
    });
}

function on_load() {
    console.log("Initializing...");

    const urlParams = new URLSearchParams(window.location.search);
    const path = urlParams.has("path") ? urlParams.get("path") : ".";
    init_parent_anchor(path);
    document.getElementById("function_filter").addEventListener("change", apply_function_filters);
    document.getElementById("function_search").addEventListener("input", apply_function_filters);
    document.getElementById("source_report").addEventListener("change", render_source_coverage);

    fetch("data/manifest.json").then(response => response.json()).then(manifest_data => {
        console.debug("Manifest: ", manifest_data);
        handle_manifest(path, manifest_data);
    });
    console.log("Initialization Complete.");
}
