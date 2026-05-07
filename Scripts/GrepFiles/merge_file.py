import os
import re
import datetime


# =================================================================
# [SECTION 0] USER SETTINGS
# =================================================================

PROJECT_ROOT_KEYWORD = "Programming"

SOURCE_EXTS = (
	".h",
	".cpp",
	".cs",
	".py",
	".json",
	".ini",
	".uproject",
	".uplugin",
)

FILE_FIND_EXTS = SOURCE_EXTS


# =================================================================
# [SECTION 1] COMMON HELPERS
# =================================================================

class TextInputParser:
	@staticmethod
	def parse_lines(raw_text):
		result = []

		for raw_line in raw_text.splitlines():
			line = raw_line.strip()

			if line == "":
				continue

			if line == "[" or line == "]" or line == "]," or line == ");":
				continue

			if line.startswith("//") == True:
				continue

			if line.startswith("raw_input") == True:
				continue

			if line.startswith("검색어:") == True:
				line = line.replace("검색어:", "", 1).strip()

			if line.startswith("#include") == True:
				cleaned_include = TextInputParser.clean_token(line)
				if cleaned_include != "":
					result.append(cleaned_include)
				continue

			quoted_items = re.findall(r'["\'](.*?)["\']', line)
			if quoted_items:
				for item in quoted_items:
					cleaned = TextInputParser.clean_token(item)
					if cleaned != "":
						result.append(cleaned)
				continue

			cleaned = TextInputParser.clean_token(line)
			if cleaned != "":
				result.append(cleaned)

		return result

	@staticmethod
	def clean_token(text):
		cleaned = text.strip()
		cleaned = cleaned.strip("[]")
		cleaned = cleaned.strip()
		cleaned = cleaned.strip('"')
		cleaned = cleaned.strip("'")
		cleaned = cleaned.rstrip(",")
		cleaned = cleaned.strip()

		return cleaned


class PathDisplay:
	@staticmethod
	def make_display_path(abs_path, root_keyword=PROJECT_ROOT_KEYWORD):
		normalized = abs_path.replace("\\", "/")
		marker = f"/{root_keyword}/"

		if marker in normalized:
			parts = normalized.split(marker, 1)
			return "{{Root}}/" + parts[1]

		return normalized


class ProjectScanner:
	@staticmethod
	def iter_files(target_exts=SOURCE_EXTS):
		project_root = os.path.abspath(".").replace("\\", "/")

		for root, dirs, files in os.walk(project_root):
			for filename in files:
				if filename.lower().endswith(target_exts) == False:
					continue

				yield os.path.join(root, filename).replace("\\", "/")


# =================================================================
# [SECTION 2] FILE FIND ENGINE
# =================================================================

class FileFinder:
	@staticmethod
	def search(raw_text, root_keyword=PROJECT_ROOT_KEYWORD):
		keywords = TextInputParser.parse_lines(raw_text)

		if not keywords:
			return "찾을 파일명/경로 키워드가 없습니다."

		results = []

		for keyword in keywords:
			results.append(f"파일찾기: {keyword}")
			match_count = 0
			keyword_lower = keyword.lower()

			for abs_path in ProjectScanner.iter_files(FILE_FIND_EXTS):
				display_path = PathDisplay.make_display_path(abs_path, root_keyword)
				filename = os.path.basename(abs_path)

				if keyword_lower not in display_path.lower() and keyword_lower not in filename.lower():
					continue

				results.append(display_path)
				match_count += 1

			if match_count == 0:
				results.append("  (결과 없음)")

			results.append("-" * 40)

		return "\n".join(results)


# =================================================================
# [SECTION 3] TEXT GREP ENGINE
# =================================================================

class TextGrep:
	@staticmethod
	def search(raw_text, root_keyword=PROJECT_ROOT_KEYWORD):
		keywords = TextInputParser.parse_lines(raw_text)

		if not keywords:
			return "검색할 키워드가 없습니다."

		results = []

		for keyword in keywords:
			results.append(f"그랩: {keyword}")
			match_count = 0

			for abs_path in ProjectScanner.iter_files(SOURCE_EXTS):
				try:
					with open(abs_path, "r", encoding="utf-8", errors="ignore") as file:
						for line_num, line_content in enumerate(file, 1):
							if keyword not in line_content:
								continue

							display_path = PathDisplay.make_display_path(abs_path, root_keyword)
							results.append(f"{display_path}:{line_num}: {line_content.rstrip()}")
							match_count += 1

				except OSError:
					continue

			if match_count == 0:
				results.append("  (결과 없음)")

			results.append("-" * 40)

		return "\n".join(results)


# =================================================================
# [SECTION 4] FILE MERGE ENGINE
# =================================================================

class FileMerger:
	@staticmethod
	def run(raw_text, tree_text, root_keyword=PROJECT_ROOT_KEYWORD, output_filename="output.txt"):
		ordered_targets = []
		seen = set()

		def add_target(path_text):
			cleaned = TextInputParser.clean_token(path_text)
			cleaned = cleaned.split("#")[0].split("//")[0].strip()

			if cleaned == "":
				return

			if cleaned in seen:
				return

			seen.add(cleaned)
			ordered_targets.append(cleaned)

		for item in TextInputParser.parse_lines(raw_text):
			add_target(item)

		for tree_file in re.findall(r"[├└]──\s+([\w\.\-/]+)", tree_text):
			if "." in tree_file:
				add_target(tree_file)

		file_map = {}

		for abs_path in ProjectScanner.iter_files(SOURCE_EXTS):
			filename = os.path.basename(abs_path)

			if filename not in file_map:
				file_map[filename] = []

			file_map[filename].append(abs_path)

		failed = []
		success_info = []
		contents = []

		for target in ordered_targets:
			filename = os.path.basename(target)
			matches = file_map.get(filename, [])
			final_path = None

			if len(matches) == 1:
				final_path = matches[0]
			elif len(matches) > 1:
				sub_path = target.replace("{{Root}}/", "").lstrip("/")
				filtered_matches = [path for path in matches if sub_path in path]

				if len(filtered_matches) == 1:
					final_path = filtered_matches[0]
				elif len(filtered_matches) > 1:
					failed.append(f"Ambiguous: {target}")
				else:
					failed.append(f"Ambiguous: {target}")
			else:
				failed.append(f"Not Found: {target}")

			if final_path is None:
				continue

			display_path = PathDisplay.make_display_path(final_path, root_keyword)

			try:
				stat_result = os.stat(final_path)
				modified_time = datetime.datetime.fromtimestamp(stat_result.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
				size_kb = f"{round(stat_result.st_size / 1024, 2)} KB"

				success_info.append({
					"display": display_path,
					"abs_path": final_path,
					"mtime": modified_time,
					"size": size_kb,
				})

				with open(final_path, "r", encoding="utf-8", errors="ignore") as file:
					contents.append((display_path, file.read()))

			except OSError:
				failed.append(f"Read Error: {display_path}")

		if failed:
			return False, failed

		if not success_info:
			return False, ["No file merged."]

		try:
			with open(output_filename, "w", encoding="utf-8") as file:
				file.write("@@@COMMENT_BEGIN\n")

				for info in success_info:
					file.write(f"File: {info['display']}\n")
					file.write(f"  - Path: {info['abs_path']}\n")
					file.write(f"  - Last Modified: {info['mtime']}\n")
					file.write(f"  - Size: {info['size']}\n\n")

				file.write("@@@COMMENT_END\n\n")

				for path, content in contents:
					file.write(f"@@@FILE_BEGIN {path}\n")
					file.write(content)
					file.write(f"\n@@@FILE_END\n\n")

			return True, []

		except OSError as error:
			return False, [str(error)]
