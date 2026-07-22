#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { XMLParser } from "fast-xml-parser";
import imageSize from "image-size";
import svgPathParser from "svg-path-parser";

const { parseSVG, makeAbsolute } = svgPathParser;

const DEFAULT_STROKE = "#000000";
const DEFAULT_FILL = "transparent";
const CURVE_SAMPLES = 8;
const SUPPORTED_IMAGE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
]);
const SUPPORTED_ICON_EXTENSIONS = new Set([
  ".svg",
  ...SUPPORTED_IMAGE_EXTENSIONS,
]);
const IMAGE_MIME_TYPES = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
};

function randomId() {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
  let id = "";
  for (let i = 0; i < 21; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return id;
}

function randomInt(max = 2 ** 31) {
  return Math.floor(Math.random() * max);
}

function parseViewBox(svgNode) {
  const viewBox = svgNode["@_viewBox"];
  if (viewBox) {
    const [x, y, width, height] = viewBox.split(/[\s,]+/).map(Number);
    return { x, y, width, height };
  }

  const width = Number.parseFloat(String(svgNode["@_width"] || "64").replace("px", ""));
  const height = Number.parseFloat(String(svgNode["@_height"] || "64").replace("px", ""));

  return { x: 0, y: 0, width, height };
}

function normalizeColor(color) {
  if (!color || color === "none") {
    return "transparent";
  }
  return color;
}

function inheritStyle(parentStyle, node) {
  const attrs = node || {};
  const next = { ...parentStyle };

  if (attrs["@_fill"] !== undefined) {
    next.fill = normalizeColor(attrs["@_fill"]);
  }
  if (attrs["@_stroke"] !== undefined) {
    next.stroke = normalizeColor(attrs["@_stroke"]);
  }
  if (attrs["@_stroke-width"] !== undefined) {
    next.strokeWidth = Number.parseFloat(attrs["@_stroke-width"]) || 0;
  }
  if (attrs["@_opacity"] !== undefined) {
    next.opacity = Number.parseFloat(attrs["@_opacity"]) * 100;
  }

  return next;
}

function applyPaintStyle(element, style) {
  element.backgroundColor =
    style.fill !== "transparent" ? style.fill : DEFAULT_FILL;
  element.strokeColor =
    style.stroke !== "transparent" ? style.stroke : DEFAULT_STROKE;
  element.strokeWidth =
    style.stroke !== "transparent" && style.strokeWidth > 0
      ? style.strokeWidth
      : 2;
  element.opacity = style.opacity ?? 100;
}

function createBaseElement(type, groupId) {
  return {
    type,
    version: 1,
    versionNonce: randomInt(),
    isDeleted: false,
    id: randomId(),
    fillStyle: "solid",
    strokeWidth: 2,
    strokeStyle: "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    strokeColor: DEFAULT_STROKE,
    backgroundColor: DEFAULT_FILL,
    seed: randomInt(),
    groupIds: [groupId],
    strokeSharpness: "sharp",
    boundElementIds: [],
  };
}

function finalizeLinearElement(element, absolutePoints) {
  if (absolutePoints.length < 2) {
    return null;
  }

  const xs = absolutePoints.map(([x]) => x);
  const ys = absolutePoints.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);

  element.x = minX;
  element.y = minY;
  element.width = maxX - minX;
  element.height = maxY - minY;
  element.points = absolutePoints.map(([x, y]) => [x - minX, y - minY]);
  element.lastCommittedPoint = null;
  element.startBinding = null;
  element.endBinding = null;
  element.startArrowhead = null;
  element.endArrowhead = null;

  return element;
}

function sampleCubic(p0, p1, p2, p3, samples = CURVE_SAMPLES) {
  const points = [];
  for (let i = 1; i <= samples; i++) {
    const t = i / samples;
    const mt = 1 - t;
    const x =
      mt ** 3 * p0[0] +
      3 * mt ** 2 * t * p1[0] +
      3 * mt * t ** 2 * p2[0] +
      t ** 3 * p3[0];
    const y =
      mt ** 3 * p0[1] +
      3 * mt ** 2 * t * p1[1] +
      3 * mt * t ** 2 * p2[1] +
      t ** 3 * p3[1];
    points.push([x, y]);
  }
  return points;
}

function sampleQuadratic(p0, p1, p2, samples = CURVE_SAMPLES) {
  const points = [];
  for (let i = 1; i <= samples; i++) {
    const t = i / samples;
    const mt = 1 - t;
    const x = mt ** 2 * p0[0] + 2 * mt * t * p1[0] + t ** 2 * p2[0];
    const y = mt ** 2 * p0[1] + 2 * mt * t * p1[1] + t ** 2 * p2[1];
    points.push([x, y]);
  }
  return points;
}

function pathCommandsToPoints(d) {
  const commands = makeAbsolute(parseSVG(d));
  const subpaths = [];
  let current = [];
  let cursor = [0, 0];

  const pushCurrent = () => {
    if (current.length >= 2) {
      subpaths.push(current);
    }
    current = [];
  };

  for (const command of commands) {
    switch (command.code) {
      case "M":
        pushCurrent();
        cursor = [command.x, command.y];
        current.push([command.x, command.y]);
        break;
      case "L":
      case "H":
      case "V":
        cursor = [command.x, command.y];
        current.push([command.x, command.y]);
        break;
      case "C":
        current.push(
          ...sampleCubic(
            cursor,
            [command.x1, command.y1],
            [command.x2, command.y2],
            [command.x, command.y],
          ),
        );
        cursor = [command.x, command.y];
        break;
      case "Q":
        current.push(
          ...sampleQuadratic(cursor, [command.x1, command.y1], [command.x, command.y]),
        );
        cursor = [command.x, command.y];
        break;
      case "Z":
        if (current.length > 0) {
          current.push([current[0][0], current[0][1]]);
        }
        break;
      default:
        if (command.x !== undefined && command.y !== undefined) {
          cursor = [command.x, command.y];
          current.push([command.x, command.y]);
        }
        break;
    }
  }

  pushCurrent();
  return subpaths;
}

function convertRect(node, style, groupId) {
  const x = Number.parseFloat(node["@_x"] || "0");
  const y = Number.parseFloat(node["@_y"] || "0");
  const width = Number.parseFloat(node["@_width"] || "0");
  const height = Number.parseFloat(node["@_height"] || "0");

  if (width <= 0 || height <= 0) {
    return [];
  }

  const element = createBaseElement("rectangle", groupId);
  element.x = x;
  element.y = y;
  element.width = width;
  element.height = height;
  applyPaintStyle(element, style);

  return [element];
}

function convertCircle(node, style, groupId) {
  const cx = Number.parseFloat(node["@_cx"] || "0");
  const cy = Number.parseFloat(node["@_cy"] || "0");
  const r = Number.parseFloat(node["@_r"] || "0");

  if (r <= 0) {
    return [];
  }

  const element = createBaseElement("ellipse", groupId);
  element.x = cx - r;
  element.y = cy - r;
  element.width = r * 2;
  element.height = r * 2;
  applyPaintStyle(element, style);

  return [element];
}

function convertEllipse(node, style, groupId) {
  const cx = Number.parseFloat(node["@_cx"] || "0");
  const cy = Number.parseFloat(node["@_cy"] || "0");
  const rx = Number.parseFloat(node["@_rx"] || "0");
  const ry = Number.parseFloat(node["@_ry"] || "0");

  if (rx <= 0 || ry <= 0) {
    return [];
  }

  const element = createBaseElement("ellipse", groupId);
  element.x = cx - rx;
  element.y = cy - ry;
  element.width = rx * 2;
  element.height = ry * 2;
  applyPaintStyle(element, style);

  return [element];
}

function convertPath(node, style, groupId) {
  const d = node["@_d"];
  if (!d) {
    return [];
  }

  const subpaths = pathCommandsToPoints(d);
  const elements = [];

  for (const subpath of subpaths) {
    if (isCircleLike(subpath)) {
      elements.push(convertCircleLikeSubpath(subpath, style, groupId));
      continue;
    }

    const element = createBaseElement("line", groupId);
    applyPaintStyle(element, style);

    const finalized = finalizeLinearElement(element, subpath);
    if (finalized) {
      elements.push(finalized);
    }
  }

  return elements;
}

function convertLine(node, style, groupId) {
  const x1 = Number.parseFloat(node["@_x1"] || "0");
  const y1 = Number.parseFloat(node["@_y1"] || "0");
  const x2 = Number.parseFloat(node["@_x2"] || "0");
  const y2 = Number.parseFloat(node["@_y2"] || "0");

  const element = createBaseElement("line", groupId);
  applyPaintStyle(element, { ...style, fill: "transparent" });

  const finalized = finalizeLinearElement(element, [
    [x1, y1],
    [x2, y2],
  ]);

  return finalized ? [finalized] : [];
}

function convertPolygonLike(node, style, groupId, attrName) {
  const raw = node[`@_${attrName}`];
  if (!raw) {
    return [];
  }

  const numbers = raw
    .trim()
    .split(/[\s,]+/)
    .map(Number)
    .filter((n) => !Number.isNaN(n));

  const points = [];
  for (let i = 0; i < numbers.length; i += 2) {
    points.push([numbers[i], numbers[i + 1]]);
  }

  if (points.length < 2) {
    return [];
  }

  if (attrName === "points") {
    points.push([points[0][0], points[0][1]]);
  }

  const element = createBaseElement("line", groupId);
  applyPaintStyle(element, style);

  const finalized = finalizeLinearElement(element, points);
  return finalized ? [finalized] : [];
}

function walkNode(node, style, groupId, elements) {
  if (!node || typeof node !== "object") {
    return;
  }

  if (Array.isArray(node)) {
    for (const child of node) {
      walkNode(child, style, groupId, elements);
    }
    return;
  }

  const nodeStyle = inheritStyle(style, node);

  if (node.rect) {
    const rects = Array.isArray(node.rect) ? node.rect : [node.rect];
    for (const rect of rects) {
      elements.push(...convertRect(rect, inheritStyle(nodeStyle, rect), groupId));
    }
  }

  if (node.circle) {
    const circles = Array.isArray(node.circle) ? node.circle : [node.circle];
    for (const circle of circles) {
      elements.push(
        ...convertCircle(circle, inheritStyle(nodeStyle, circle), groupId),
      );
    }
  }

  if (node.ellipse) {
    const ellipses = Array.isArray(node.ellipse) ? node.ellipse : [node.ellipse];
    for (const ellipse of ellipses) {
      elements.push(
        ...convertEllipse(ellipse, inheritStyle(nodeStyle, ellipse), groupId),
      );
    }
  }

  if (node.path) {
    const paths = Array.isArray(node.path) ? node.path : [node.path];
    for (const pathNode of paths) {
      elements.push(
        ...convertPath(pathNode, inheritStyle(nodeStyle, pathNode), groupId),
      );
    }
  }

  if (node.line) {
    const lines = Array.isArray(node.line) ? node.line : [node.line];
    for (const line of lines) {
      elements.push(...convertLine(line, inheritStyle(nodeStyle, line), groupId));
    }
  }

  if (node.polygon) {
    const polygons = Array.isArray(node.polygon) ? node.polygon : [node.polygon];
    for (const polygon of polygons) {
      elements.push(
        ...convertPolygonLike(polygon, inheritStyle(nodeStyle, polygon), groupId, "points"),
      );
    }
  }

  if (node.polyline) {
    const polylines = Array.isArray(node.polyline) ? node.polyline : [node.polyline];
    for (const polyline of polylines) {
      elements.push(
        ...convertPolygonLike(
          polyline,
          inheritStyle(nodeStyle, polyline),
          groupId,
          "points",
        ),
      );
    }
  }

  if (node.g) {
    const groups = Array.isArray(node.g) ? node.g : [node.g];
    for (const group of groups) {
      walkNode(group, nodeStyle, groupId, elements);
    }
  }
}

function isCircleLike(points) {
  if (points.length < 6) {
    return false;
  }

  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const width = maxX - minX;
  const height = maxY - minY;

  if (width <= 0 || height <= 0 || width > 6 || height > 6) {
    return false;
  }

  const ratio = width / height;
  return ratio > 0.7 && ratio < 1.3;
}

function convertCircleLikeSubpath(subpath, style, groupId) {
  const xs = subpath.map(([x]) => x);
  const ys = subpath.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const element = createBaseElement("ellipse", groupId);
  element.x = minX;
  element.y = minY;
  element.width = maxX - minX;
  element.height = maxY - minY;
  applyPaintStyle(element, style);

  return element;
}

function sortElements(elements) {
  const order = { rectangle: 0, ellipse: 1, line: 2, arrow: 3 };
  return [...elements].sort(
    (a, b) => (order[a.type] ?? 99) - (order[b.type] ?? 99),
  );
}

function normalizeElements(elements) {
  if (elements.length === 0) {
    return elements;
  }

  let minX = Infinity;
  let minY = Infinity;

  for (const element of elements) {
    minX = Math.min(minX, element.x);
    minY = Math.min(minY, element.y);
  }

  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    return elements;
  }

  for (const element of elements) {
    element.x -= minX;
    element.y -= minY;
  }

  return elements;
}

export function convertSvgToExcalidrawLibrary(svgContent, options = {}) {
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: "@_",
  });

  const parsed = parser.parse(svgContent);
  const svgNode = parsed.svg;

  if (!svgNode) {
    throw new Error("Invalid SVG: missing <svg> root element");
  }

  const viewBox = parseViewBox(svgNode);
  const groupId = randomId();
  const elements = [];

  const rootStyle = inheritStyle(
    {
      fill: DEFAULT_FILL,
      stroke: DEFAULT_STROKE,
      strokeWidth: 0,
      opacity: 100,
    },
    svgNode,
  );

  walkNode(svgNode, rootStyle, groupId, elements);

  const normalized =
    options.normalize !== false ? normalizeElements(elements) : elements;

  return {
    type: "excalidrawlib",
    version: 1,
    library: [sortElements(normalized)],
    files: {},
    metadata: {
      sourceViewBox: viewBox,
      elementCount: normalized.length,
    },
  };
}

function getInputKind(inputPath) {
  const ext = path.extname(inputPath).toLowerCase();
  if (ext === ".svg") {
    return "svg";
  }
  if (SUPPORTED_IMAGE_EXTENSIONS.has(ext)) {
    return "image";
  }
  return null;
}

function isSupportedIconFile(filePath) {
  return SUPPORTED_ICON_EXTENSIONS.has(path.extname(filePath).toLowerCase());
}

function collectInputPaths(inputs) {
  const collected = [];

  for (const input of inputs) {
    const resolved = path.resolve(input);
    let stat;

    try {
      stat = fs.statSync(resolved);
    } catch {
      throw new Error(`Input not found: ${input}`);
    }

    if (stat.isDirectory()) {
      const iconFiles = fs
        .readdirSync(resolved)
        .filter((name) => isSupportedIconFile(name))
        .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))
        .map((name) => path.join(resolved, name));

      if (iconFiles.length === 0) {
        console.error(
          `Warning: no .svg or image files found in ${path.relative(process.cwd(), resolved) || "."}`,
        );
      } else {
        console.error(
          `Found ${iconFiles.length} icon file(s) in ${path.relative(process.cwd(), resolved) || "."}`,
        );
      }

      collected.push(...iconFiles);
      continue;
    }

    if (stat.isFile()) {
      collected.push(resolved);
      continue;
    }

    throw new Error(`Not a file or directory: ${input}`);
  }

  return [...new Set(collected)];
}

function defaultOutputPath(rawInputs, resolvedInputs) {
  if (resolvedInputs.length === 1) {
    const onlyInput = path.resolve(rawInputs[0]);
    if (fs.statSync(onlyInput).isDirectory()) {
      const dirName = path.basename(onlyInput);
      return `${dirName === "." ? "icons" : dirName}.excalidrawlib`;
    }

    return `${path.basename(resolvedInputs[0], path.extname(resolvedInputs[0]))}.excalidrawlib`;
  }

  return "icons.excalidrawlib";
}

function generateFileId(buffer) {
  return crypto.createHash("sha1").update(buffer).digest("hex");
}

export function convertImageToExcalidrawLibrary(inputPath, options = {}) {
  const buffer = fs.readFileSync(inputPath);
  const ext = path.extname(inputPath).toLowerCase();
  const mimeType = IMAGE_MIME_TYPES[ext];

  if (!mimeType) {
    throw new Error(`Unsupported image format: ${ext}`);
  }

  const dimensions = imageSize(buffer);
  if (!dimensions.width || !dimensions.height) {
    throw new Error(`Could not read image dimensions from ${inputPath}`);
  }

  const fileId = generateFileId(buffer);
  const dataURL = `data:${mimeType};base64,${buffer.toString("base64")}`;
  const groupId = randomId();
  const now = Date.now();

  const element = createBaseElement("image", groupId);
  element.x = 0;
  element.y = 0;
  element.width = dimensions.width;
  element.height = dimensions.height;
  element.strokeColor = "transparent";
  element.backgroundColor = "transparent";
  element.strokeSharpness = "round";
  element.status = "saved";
  element.fileId = fileId;
  element.scale = [1, 1];
  element.crop = null;
  element.link = null;
  element.locked = false;
  element.updated = now;

  return {
    type: "excalidrawlib",
    version: 1,
    library: [[element]],
    files: {
      [fileId]: {
        mimeType,
        id: fileId,
        dataURL,
        created: now,
        lastRetrieved: now,
      },
    },
    metadata: {
      elementCount: 1,
      sourceFile: path.basename(inputPath),
    },
  };
}

export function convertInputToExcalidrawLibrary(inputPath, options = {}) {
  const kind = getInputKind(inputPath);
  if (kind === "svg") {
    const svgContent = fs.readFileSync(inputPath, "utf8");
    return convertSvgToExcalidrawLibrary(svgContent, options);
  }
  if (kind === "image") {
    return convertImageToExcalidrawLibrary(inputPath, options);
  }

  const ext = path.extname(inputPath) || "(no extension)";
  throw new Error(
    `Unsupported file type ${ext}. Use SVG or PNG/JPG/GIF/WebP images.`,
  );
}

function printUsage() {
  console.log(`Usage: node svg-to-excalidrawlib.mjs <input> [more inputs...] [options]

Convert SVG or image files (PNG, JPG, GIF, WebP) into an Excalidraw library (.excalidrawlib).

Each input can be:
  - a single icon file (.svg, .png, ...)
  - a directory (all .svg and image files in that folder are included, non-recursive)

Examples:
  node svg-to-excalidrawlib.mjs icon.svg -o my-icons.excalidrawlib
  node svg-to-excalidrawlib.mjs icon1.svg icon2.png -o my-icons.excalidrawlib
  node svg-to-excalidrawlib.mjs . -o aws-icons.excalidrawlib

Options:
  -o, --output <file>   Output file path (default: derived from input name)
  --append <library>    Append converted icons to an existing .excalidrawlib file
  --no-normalize        Keep original SVG coordinates instead of shifting to origin
`);
}

function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    printUsage();
    process.exit(args.length === 0 ? 1 : 0);
  }

  let outputPath;
  let appendPath;
  let normalize = true;
  const rawInputs = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "-o" || arg === "--output") {
      outputPath = args[++i];
    } else if (arg === "--append") {
      appendPath = args[++i];
    } else if (arg === "--no-normalize") {
      normalize = false;
    } else if (!arg.startsWith("-")) {
      rawInputs.push(arg);
    }
  }

  if (rawInputs.length === 0) {
    console.error("Error: at least one input file or directory is required.");
    printUsage();
    process.exit(1);
  }

  const inputPaths = collectInputPaths(rawInputs);

  if (inputPaths.length === 0) {
    console.error("Error: no supported icon files to convert.");
    process.exit(1);
  }

  const libraryItems = [];
  const files = {};

  for (const inputPath of inputPaths) {
    try {
      const converted = convertInputToExcalidrawLibrary(inputPath, { normalize });
      libraryItems.push(converted.library[0]);
      Object.assign(files, converted.files || {});
      console.error(
        `Converted ${path.basename(inputPath)} -> ${converted.library[0].length} element(s)`,
      );
    } catch (error) {
      console.error(`Error converting ${path.basename(inputPath)}: ${error.message}`);
      process.exit(1);
    }
  }

  let libraryFile = {
    type: "excalidrawlib",
    version: 1,
    library: libraryItems,
    ...(Object.keys(files).length > 0 ? { files } : {}),
  };

  if (appendPath) {
    const existing = JSON.parse(fs.readFileSync(appendPath, "utf8"));
    if (existing.type !== "excalidrawlib" || !Array.isArray(existing.library)) {
      throw new Error(`Invalid library file: ${appendPath}`);
    }
    libraryFile = {
      ...existing,
      library: [...existing.library, ...libraryItems],
      files: { ...(existing.files || {}), ...files },
    };
    outputPath = outputPath || appendPath;
  }

  if (!outputPath) {
    outputPath = defaultOutputPath(rawInputs, inputPaths);
  }

  const { metadata, ...output } = libraryFile;
  void metadata;

  fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
  console.error(`Wrote ${outputPath} (${libraryFile.library.length} library item(s))`);
}

const isMain =
  process.argv[1] &&
  path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));

if (isMain) {
  try {
    main();
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}
