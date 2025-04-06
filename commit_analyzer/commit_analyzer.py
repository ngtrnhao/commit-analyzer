import os
from git import Repo
from rich.console import Console
from rich.prompt import Prompt
import re
import ast
from typing import Dict, Set, List, Optional, Tuple
from difflib import unified_diff
import json
from collections import defaultdict
import requests
from transformers import pipeline

console = Console()

# Initialize AI models
try:
    # Hugging Face model for code analysis
    code_analyzer = pipeline("text-classification", model="microsoft/codebert-base")
except:
    console.print("[yellow]Warning: Could not load Hugging Face model. Using fallback analysis.[/yellow]")

def get_git_diff(repo_path='.') -> Tuple[str, str]:
    """Get the git diff of staged changes and their original content."""
    repo = Repo(repo_path)
    diff = repo.git.diff('--staged')
    
    # Get original content of changed files
    original_content = {}
    for file in repo.git.diff('--staged', '--name-only').split('\n'):
        if file:
            try:
                original_content[file] = repo.git.show(f'HEAD:{file}')
            except:
                original_content[file] = ''
    
    return diff, original_content

def parse_python_file(file_path: str) -> Dict:
    """Parse a Python file to extract code structure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        analysis = {
            'functions': set(),
            'classes': set(),
            'imports': set(),
            'variables': set(),
            'methods': set(),
            'decorators': set(),
            'test_functions': set()
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis['functions'].add(node.name)
                if node.name.startswith('test_'):
                    analysis['test_functions'].add(node.name)
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        analysis['decorators'].add(decorator.id)
            elif isinstance(node, ast.ClassDef):
                analysis['classes'].add(node.name)
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        analysis['methods'].add(f"{node.name}.{item.name}")
            elif isinstance(node, ast.Import):
                for name in node.names:
                    analysis['imports'].add(name.name)
            elif isinstance(node, ast.ImportFrom):
                analysis['imports'].add(node.module)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis['variables'].add(target.id)
        
        return analysis
    except Exception as e:
        console.print(f"[red]Error parsing {file_path}: {str(e)}[/red]")
        return {}

def analyze_js_file(file_path: str) -> Dict:
    """Analyze a JavaScript file to extract code structure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'functions': set(),
            'classes': set(),
            'imports': set(),
            'variables': set(),
            'methods': set(),
            'components': set()
        }
        
        # Extract function declarations
        function_matches = re.finditer(r'function\s+(\w+)\s*\(', content)
        analysis['functions'].update(match.group(1) for match in function_matches)
        
        # Extract class declarations
        class_matches = re.finditer(r'class\s+(\w+)\s*{', content)
        analysis['classes'].update(match.group(1) for match in class_matches)
        
        # Extract imports
        import_matches = re.finditer(r'import\s+.*?from\s+[\'"](.*?)[\'"]', content)
        analysis['imports'].update(match.group(1) for match in import_matches)
        
        # Extract React components
        component_matches = re.finditer(r'const\s+(\w+)\s*=\s*\(\)\s*=>\s*{', content)
        analysis['components'].update(match.group(1) for match in component_matches)
        
        return analysis
    except Exception as e:
        console.print(f"[red]Error analyzing {file_path}: {str(e)}[/red]")
        return {}

def analyze_package_json(file_path: str) -> Dict:
    """Analyze package.json for dependency changes."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'dependencies': set(),
            'dev_dependencies': set(),
            'scripts': set()
        }
        
        # Extract dependencies
        dep_matches = re.finditer(r'"dependencies":\s*{([^}]*)}', content)
        for match in dep_matches:
            deps = re.finditer(r'"(\w+)"\s*:', match.group(1))
            analysis['dependencies'].update(dep.group(1) for dep in deps)
        
        # Extract devDependencies
        dev_dep_matches = re.finditer(r'"devDependencies":\s*{([^}]*)}', content)
        for match in dev_dep_matches:
            deps = re.finditer(r'"(\w+)"\s*:', match.group(1))
            analysis['dev_dependencies'].update(dep.group(1) for dep in deps)
        
        # Extract scripts
        script_matches = re.finditer(r'"scripts":\s*{([^}]*)}', content)
        for match in script_matches:
            scripts = re.finditer(r'"(\w+)"\s*:', match.group(1))
            analysis['scripts'].update(script.group(1) for script in scripts)
        
        return analysis
    except Exception as e:
        console.print(f"[red]Error analyzing {file_path}: {str(e)}[/red]")
        return {}

def analyze_code_structure(file_path: str, content: str) -> Dict:
    """Analyze the structure of a code file."""
    try:
        # Determine file type
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.py':
            return parse_python_file(file_path)
        elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            return analyze_js_file(file_path)
        elif file_ext == '.md':
            return analyze_markdown_file(file_path)
        elif file_ext in ['.json', '.yaml', '.yml']:
            return analyze_config_file(file_path)
        else:
            return {
                'functions': [],
                'classes': [],
                'imports': [],
                'variables': [],
                'methods': [],
                'decorators': [],
                'test_functions': []
            }
    except Exception as e:
        console.print(f"[red]Error analyzing {file_path}: {str(e)}[/red]")
        return {
            'functions': [],
            'classes': [],
            'imports': [],
            'variables': [],
            'methods': [],
            'decorators': [],
            'test_functions': []
        }

def analyze_file_changes(diff: str) -> Dict:
    """Analyze changes in files with more detailed categorization."""
    changes = {
        'files': set(),
        'added_files': set(),
        'deleted_files': set(),
        'modified_files': set(),
        'renamed_files': set(),
        'file_types': defaultdict(set),
        'content_changes': defaultdict(lambda: {'added': [], 'removed': []})
    }
    
    current_file = None
    for line in diff.split('\n'):
        if line.startswith('diff --git'):
            parts = line.split()
            # Extract both a/ and b/ paths
            a_path = parts[2][2:]  # Remove 'a/' prefix
            b_path = parts[3][2:]  # Remove 'b/' prefix
            current_file = b_path  # Use the new path as current
            changes['files'].add(current_file)
            file_ext = os.path.splitext(current_file)[1]
            changes['file_types'][file_ext].add(current_file)
        
        elif line.startswith('new file mode'):
            changes['added_files'].add(current_file)
        
        elif line.startswith('deleted file mode'):
            changes['deleted_files'].add(current_file)
        
        elif line.startswith('rename from'):
            old_file = line.split(' ')[2]
            next_line = next(line for line in diff.split('\n') if line.startswith('rename to'))
            new_file = next_line.split(' ')[2]
            changes['renamed_files'].add((old_file, new_file))
        
        elif line.startswith('+') and not line.startswith('+++'):
            if current_file:
                changes['content_changes'][current_file]['added'].append(line[1:])
        
        elif line.startswith('-') and not line.startswith('---'):
            if current_file:
                changes['content_changes'][current_file]['removed'].append(line[1:])
    
    # Determine modified files (files that are not added, deleted, or renamed)
    all_renamed = {old for old, new in changes['renamed_files']} | {new for old, new in changes['renamed_files']}
    changes['modified_files'] = changes['files'] - changes['added_files'] - changes['deleted_files'] - all_renamed
    
    return changes

def analyze_diff_changes(diff_lines: List[str], original_content: Dict[str, str]) -> Dict:
    """Analyze code changes with more detailed categorization."""
    changes = {
        'security': [],
        'features': [],
        'fixes': [],
        'refactors': [],
        'performance': [],
        'components': [],
        'dependencies': [],
        'scripts': [],
        'tests': [],
        'docs': [],
        'config': [],
        'style': [],
        'added_lines': [],
        'removed_lines': [],
        'feature_details': defaultdict(list),
        'semantic_changes': defaultdict(list),
        'code_metrics': {
            'lines_added': 0,
            'lines_removed': 0,
            'files_changed': 0,
            'complexity_changes': 0,
            'functions_added': 0,
            'functions_modified': 0,
            'classes_added': 0,
            'classes_modified': 0,
            'imports_added': 0,
            'imports_removed': 0
        }
    }
    
    current_file = None
    current_function = None
    current_class = None
    context_lines = []
    
    for line in diff_lines:
        if line.startswith('diff --git'):
            if current_file and context_lines:
                analyze_context(changes, current_file, context_lines)
            current_file = line.split(' ')[2][2:]
            changes['code_metrics']['files_changed'] += 1
            current_function = None
            current_class = None
            context_lines = []
        
        elif line.startswith('+') and not line.startswith('+++'):
            content = line[1:]
            changes['added_lines'].append(content)
            changes['code_metrics']['lines_added'] += 1
            context_lines.append(('add', content))
            
            if current_file:
                analyze_line_content(content, current_file, changes)
        
        elif line.startswith('-') and not line.startswith('---'):
            content = line[1:]
            changes['removed_lines'].append(content)
            changes['code_metrics']['lines_removed'] += 1
            context_lines.append(('remove', content))
            
            if current_file:
                if 'def ' in content:
                    changes['code_metrics']['functions_modified'] += 1
                    func_name = content.split('def ')[1].split('(')[0].strip()
                    changes['semantic_changes'][current_file].append(f'modify {func_name} function')
                elif 'class ' in content:
                    changes['code_metrics']['classes_modified'] += 1
                    class_name = content.split('class ')[1].split('(')[0].strip()
                    changes['semantic_changes'][current_file].append(f'modify {class_name} class')
        else:
            context_lines.append(('context', line))
    
    if current_file and context_lines:
        analyze_context(changes, current_file, context_lines)
    
    return changes

def learn_from_github_commits(repo_path: str = '.') -> Dict:
    """Learn patterns from existing commits in the repository."""
    try:
        repo = Repo(repo_path)
        commit_patterns = {
            'types': defaultdict(int),
            'scopes': defaultdict(int),
            'descriptions': defaultdict(int),
            'common_patterns': defaultdict(int)
        }
        
        # Analyze last 100 commits
        for commit in list(repo.iter_commits())[:100]:
            message = commit.message.strip()
            if not message:
                continue
                
            # Split commit message into parts
            parts = message.split(':', 1)
            if len(parts) == 2:
                type_scope = parts[0].strip()
                description = parts[1].strip()
                
                # Analyze type and scope
                if '(' in type_scope:
                    commit_type, scope = type_scope.split('(', 1)
                    scope = scope.rstrip(')')
                    commit_patterns['types'][commit_type.strip()] += 1
                    commit_patterns['scopes'][scope.strip()] += 1
                else:
                    commit_patterns['types'][type_scope] += 1
                
                # Analyze description patterns
                words = description.lower().split()
                for i in range(len(words) - 1):
                    pattern = f"{words[i]} {words[i+1]}"
                    commit_patterns['common_patterns'][pattern] += 1
                
                # Store full descriptions
                commit_patterns['descriptions'][description] += 1
        
        return commit_patterns
    except Exception as e:
        console.print(f"[red]Error learning from commits: {str(e)}[/red]")
        return {}

def generate_commit_type(changes: Dict, file_changes: Dict, commit_patterns: Dict) -> str:
    """Generate commit type based on changes and learned patterns."""
    # Get most common commit types from patterns
    common_types = sorted(commit_patterns['types'].items(), key=lambda x: x[1], reverse=True)
    
    if changes['security']:
        return '🔒 security'
    elif changes['fixes']:
        return '🐛 fix'
    elif changes['features']:
        return '✨ feat'
    elif changes['refactors']:
        return '🔄 refactor'
    elif changes['performance']:
        return '⚡ perf'
    elif changes['docs']:
        return '📚 docs'
    elif changes['tests']:
        return '🧪 test'
    elif changes['style']:
        return '💅 style'
    elif changes['dependencies']:
        return '📦 deps'
    elif changes['scripts']:
        return '🔧 chore'
    elif common_types:
        return common_types[0][0]  # Use most common type
    return '🔧 chore'

def generate_commit_scope(changes: Dict, file_changes: Dict, commit_patterns: Dict) -> Optional[str]:
    """Generate commit scope based on changes and learned patterns."""
    # Get all changed files
    files = file_changes['files']
    if not files:
        return None
        
    # Get common directory prefix
    dirs = [os.path.dirname(f).split('/')[0] for f in files]
    common_dirs = set(dirs)
    
    # If all files are in the same directory, use that as scope
    if len(common_dirs) == 1:
        return list(common_dirs)[0]
        
    # If files are in different directories, try to find a common parent
    if len(common_dirs) > 1:
        # Get the shortest common prefix
        prefix = os.path.commonprefix([f.split('/')[0] for f in files])
        if prefix:
            return prefix
            
    # Check learned patterns for scope
    common_scopes = sorted(commit_patterns['scopes'].items(), key=lambda x: x[1], reverse=True)
    if common_scopes:
        return common_scopes[0][0]
            
    return None

def analyze_file_content_changes(file_path: str, original_content: str, modified_content: str) -> Dict:
    """Analyze the specific changes in a file's content."""
    changes = {
        'metadata': set(),
        'dependencies': set(),
        'entry_points': set(),
        'descriptions': set(),
        'classifiers': set(),
        'other': set()
    }
    
    # Split content into lines for comparison
    original_lines = original_content.split('\n')
    modified_lines = modified_content.split('\n')
    
    # Find added and modified lines
    for line in modified_lines:
        if line not in original_lines:
            # Check for metadata changes
            if 'name=' in line or 'version=' in line:
                changes['metadata'].add(line.strip())
            # Check for dependency changes
            elif 'install_requires' in line or 'requires=' in line:
                changes['dependencies'].add(line.strip())
            # Check for entry point changes
            elif 'entry_points' in line or 'console_scripts' in line:
                changes['entry_points'].add(line.strip())
            # Check for description changes
            elif 'description=' in line or 'long_description' in line:
                changes['descriptions'].add(line.strip())
            # Check for classifier changes
            elif 'classifiers=' in line or 'Programming Language ::' in line:
                changes['classifiers'].add(line.strip())
            else:
                changes['other'].add(line.strip())
    
    return changes

def generate_detailed_commit_description(changes: Dict, file_changes: Dict, commit_patterns: Dict) -> str:
    """Generate a detailed commit description based on comprehensive analysis and learned patterns."""
    desc_parts = []
    
    # Group changes by file
    file_changes_map = defaultdict(list)
    for file, changes_list in changes['semantic_changes'].items():
        # Get file name without path
        file_name = os.path.basename(file)
        for change in changes_list:
            file_changes_map[file_name].append(change)
    
    # Process each file's changes
    for file_name, changes_list in file_changes_map.items():
        # Remove duplicates and sort
        unique_changes = sorted(set(changes_list))
        
        # Group similar changes
        grouped_changes = defaultdict(list)
        for change in unique_changes:
            action = change.split()[0]
            grouped_changes[action].append(change)
        
        # Create description parts for each group
        file_parts = []
        for action, change_list in grouped_changes.items():
            if len(change_list) == 1:
                file_parts.append(change_list[0])
            else:
                # Find common prefix
                common_prefix = os.path.commonprefix([c[len(action):] for c in change_list])
                if common_prefix:
                    file_parts.append(f"{action}{common_prefix} ({len(change_list)} changes)")
                else:
                    # Take first 2 changes and count the rest
                    file_parts.append(f"{action} {', '.join(c[len(action):] for c in change_list[:2])}")
                    if len(change_list) > 2:
                        file_parts[-1] += f" and {len(change_list) - 2} more"
        
        # Add file description if there are changes
        if file_parts:
            desc_parts.append(f"{file_name}: {'; '.join(file_parts)}")
    
    # Add file operations
    file_ops = []
    if file_changes['added_files']:
        added_count = len(file_changes['added_files'])
        file_ops.append(f"add {added_count} file{'s' if added_count > 1 else ''}")
    if file_changes['deleted_files']:
        deleted_count = len(file_changes['deleted_files'])
        file_ops.append(f"remove {deleted_count} file{'s' if deleted_count > 1 else ''}")
    if file_changes['renamed_files']:
        renamed_files = [f"{os.path.basename(old)} → {os.path.basename(new)}" 
                        for old, new in file_changes['renamed_files']]
        file_ops.append(f"rename {', '.join(renamed_files)}")
    
    if file_ops:
        desc_parts.append(f"files: {'; '.join(file_ops)}")
    
    # Add metrics if significant
    metrics = changes['code_metrics']
    if metrics['lines_added'] + metrics['lines_removed'] > 50:  # Only show for significant changes
        desc_parts.append(f"({metrics['lines_added']}+/{metrics['lines_removed']}- lines)")
    
    # Join all parts with semicolons and format
    return '; '.join(desc_parts) or "update code"

def analyze_changes(diff: str, original_content: Dict[str, str]) -> Optional[str]:
    """Analyze the changes to generate a detailed commit message."""
    if not diff:
        return "No changes to commit"
    
    try:
        # Learn from existing commits
        commit_patterns = learn_from_github_commits()
        
        # Analyze file and code changes
        file_changes = analyze_file_changes(diff)
        code_changes = analyze_diff_changes(diff.split('\n'), original_content)
        
        # Analyze code structure for modified files
        for file in file_changes['modified_files']:
            if file in original_content:
                structure = analyze_code_structure(file, original_content[file])
                # Use structure analysis to enhance change detection
                if structure['functions']:
                    code_changes['components'].append(file)
        
        # Generate commit parts using learned patterns
        commit_type = generate_commit_type(code_changes, file_changes, commit_patterns)
        commit_scope = generate_commit_scope(code_changes, file_changes, commit_patterns)
        commit_desc = generate_detailed_commit_description(code_changes, file_changes, commit_patterns)
        
        # Show detailed analysis with enhanced styling
        console.print("\n[bold cyan]📊 Change Analysis Report[/bold cyan]")
        console.print("[bold cyan]=" * 50 + "[/bold cyan]")
        
        # Show file operations with icons
        if file_changes['added_files'] or file_changes['deleted_files'] or file_changes['renamed_files']:
            console.print("\n[bold]📁 File Operations[/bold]")
            console.print("[bold cyan]-" * 30 + "[/bold cyan]")
            if file_changes['added_files']:
                console.print(f"✨ [green]Added:[/green] {', '.join(sorted(file_changes['added_files']))}")
            if file_changes['deleted_files']:
                console.print(f"🗑️ [red]Deleted:[/red] {', '.join(sorted(file_changes['deleted_files']))}")
            if file_changes['renamed_files']:
                console.print(f"🔄 [yellow]Renamed:[/yellow] {', '.join(f'{old} → {new}' for old, new in sorted(file_changes['renamed_files']))}")
        
        # Show content changes with icons
        console.print("\n[bold]📝 Content Changes[/bold]")
        console.print("[bold cyan]-" * 30 + "[/bold cyan]")
        for category in ['security', 'features', 'fixes', 'refactors', 'performance', 
                        'tests', 'docs', 'config', 'dependencies']:
            if code_changes[category]:
                icon = {
                    'security': '🔒',
                    'features': '✨',
                    'fixes': '🐛',
                    'refactors': '🔄',
                    'performance': '⚡',
                    'tests': '🧪',
                    'docs': '📚',
                    'config': '⚙️',
                    'dependencies': '📦'
                }[category]
                color = {
                    'security': 'red',
                    'features': 'green',
                    'fixes': 'yellow',
                    'refactors': 'cyan',
                    'performance': 'magenta',
                    'tests': 'blue',
                    'docs': 'white',
                    'config': 'cyan',
                    'dependencies': 'blue'
                }[category]
                console.print(f"{icon} [{color}]{category.title()}:[/{color}] {', '.join(sorted(code_changes[category]))}")
        
        # Show detailed code metrics with icons
        metrics = code_changes['code_metrics']
        console.print("\n[bold]📈 Code Metrics[/bold]")
        console.print("[bold cyan]-" * 30 + "[/bold cyan]")
        console.print(f"📂 [blue]Files changed:[/blue] {metrics['files_changed']}")
        console.print(f"➕ [green]Lines added:[/green] {metrics['lines_added']}")
        console.print(f"➖ [red]Lines removed:[/red] {metrics['lines_removed']}")
        if metrics['functions_added'] > 0:
            console.print(f"➕ [green]Functions added:[/green] {metrics['functions_added']}")
        if metrics['functions_modified'] > 0:
            console.print(f"✏️ [yellow]Functions modified:[/yellow] {metrics['functions_modified']}")
        if metrics['classes_added'] > 0:
            console.print(f"➕ [green]Classes added:[/green] {metrics['classes_added']}")
        if metrics['classes_modified'] > 0:
            console.print(f"✏️ [yellow]Classes modified:[/yellow] {metrics['classes_modified']}")
        if metrics['imports_added'] > 0:
            console.print(f"📦 [blue]Imports added:[/blue] {metrics['imports_added']}")
        if metrics['imports_removed'] > 0:
            console.print(f"🗑️ [red]Imports removed:[/red] {metrics['imports_removed']}")
        
        # Show semantic changes
        if code_changes['semantic_changes']:
            console.print("\n[bold]🔍 Semantic Changes[/bold]")
            console.print("[bold cyan]-" * 30 + "[/bold cyan]")
            for file, changes in code_changes['semantic_changes'].items():
                console.print(f"📄 [cyan]{file}:[/cyan]")
                for change in sorted(set(changes)):
                    console.print(f"  • {change}")
        
        # Show learned patterns
        if commit_patterns['types'] or commit_patterns['scopes'] or commit_patterns['common_patterns']:
            console.print("\n[bold]📚 Learned Patterns[/bold]")
            console.print("[bold cyan]-" * 30 + "[/bold cyan]")
            if commit_patterns['types']:
                console.print(f"📝 Common types: {', '.join(sorted(commit_patterns['types'].keys()))}")
            if commit_patterns['scopes']:
                console.print(f"🎯 Common scopes: {', '.join(sorted(commit_patterns['scopes'].keys()))}")
            if commit_patterns['common_patterns']:
                console.print(f"🔍 Common patterns: {', '.join(sorted(commit_patterns['common_patterns'].keys())[:5])}...")
        
        # Construct commit message with enhanced formatting
        message = f"{commit_type}"
        if commit_scope:
            message += f"({commit_scope})"
        message += f": {commit_desc}"
        
        # Add detailed metrics
        metrics = code_changes['code_metrics']
        if metrics['lines_added'] + metrics['lines_removed'] > 0:
            message += f" ({metrics['lines_added']}+/{metrics['lines_removed']}- lines)"
        
        # Show suggested commit message with enhanced styling
        console.print("\n[bold]💡 Suggested Commit Message[/bold]")
        console.print("[bold cyan]-" * 30 + "[/bold cyan]")
        console.print(f"[bold cyan]{message}[/bold cyan]")
        console.print("[bold cyan]=" * 50 + "[/bold cyan]")
        
        return message
    except Exception as e:
        console.print(f"[red]❌ Error generating commit message: {str(e)}[/red]")
        return None

def analyze_line_content(line: str, file: str, changes: Dict) -> None:
    """Analyze a single line's content with context awareness."""
    # Function changes
    if 'def ' in line:
        func_name = line.split('def ')[1].split('(')[0].strip()
        if 'test_' in func_name:
            changes['tests'].append(file)
            changes['semantic_changes'][file].append(f"add test function {func_name}")
        else:
            changes['features'].append(file)
            changes['semantic_changes'][file].append(f"add function {func_name}")
    
    # Class changes
    elif 'class ' in line:
        class_name = line.split('class ')[1].split('(')[0].strip()
        if 'Test' in class_name:
            changes['tests'].append(file)
            changes['semantic_changes'][file].append(f"add test class {class_name}")
        else:
            changes['features'].append(file)
            changes['semantic_changes'][file].append(f"add class {class_name}")
    
    # Import changes
    elif re.search(r'^import\s+|^from\s+.*\s+import\s+', line):
        changes['dependencies'].append(file)
        changes['semantic_changes'][file].append("update dependencies")
    
    # Documentation changes
    elif re.search(r'"""|\'\'\'|#\s*\w+', line):
        changes['docs'].append(file)
        changes['semantic_changes'][file].append("update documentation")
    
    # Configuration changes
    elif re.search(r'config|settings|env|\.env|\.json|\.yaml|\.yml', line, re.IGNORECASE):
        changes['config'].append(file)
        changes['semantic_changes'][file].append("update configuration")
    
    # Security changes
    elif re.search(r'password|secret|key|token|auth|crypt', line, re.IGNORECASE):
        changes['security'].append(file)
        changes['semantic_changes'][file].append("enhance security")
    
    # Fix changes
    elif re.search(r'fix|bug|error|exception|issue|crash|problem', line, re.IGNORECASE):
        changes['fixes'].append(file)
        changes['semantic_changes'][file].append("fix issues")
    
    # Performance changes
    elif re.search(r'performance|optimize|speed|memory|cpu|cache', line, re.IGNORECASE):
        changes['performance'].append(file)
        changes['semantic_changes'][file].append("improve performance")
    
    # Refactor changes
    elif re.search(r'refactor|cleanup|improve|enhance|update', line, re.IGNORECASE):
        changes['refactors'].append(file)
        changes['semantic_changes'][file].append("refactor code")

def analyze_context(changes: Dict, file: str, context_lines: List[Tuple[str, str]]):
    """Analyze the context of changes to understand the broader impact."""
    if not context_lines:
        return
        
    # Group changes by their type (add/remove/context)
    added_lines = [line for type_, line in context_lines if type_ == 'add']
    removed_lines = [line for type_, line in context_lines if type_ == 'remove']
    context_lines = [line for type_, line in context_lines if type_ == 'context']
    
    # Analyze function context
    for i, line in enumerate(context_lines):
        if 'def ' in line:
            func_name = line.split('def ')[1].split('(')[0].strip()
            # Look at surrounding lines to understand function purpose
            surrounding_lines = context_lines[max(0, i-2):min(len(context_lines), i+3)]
            if any('test' in l.lower() for l in surrounding_lines):
                changes['tests'].append(file)
                changes['semantic_changes'][file].append(f'add test for {func_name}')
            elif any('doc' in l.lower() or '"""' in l for l in surrounding_lines):
                changes['docs'].append(file)
                changes['semantic_changes'][file].append(f'add documentation for {func_name}')
            else:
                changes['features'].append(file)
                changes['semantic_changes'][file].append(f'add {func_name} function')
    
    # Analyze class context
    for i, line in enumerate(context_lines):
        if 'class ' in line:
            class_name = line.split('class ')[1].split('(')[0].strip()
            # Look at surrounding lines to understand class purpose
            surrounding_lines = context_lines[max(0, i-2):min(len(context_lines), i+3)]
            if any('test' in l.lower() for l in surrounding_lines):
                changes['tests'].append(file)
                changes['semantic_changes'][file].append(f'add test class {class_name}')
            elif any('model' in l.lower() or 'schema' in l.lower() for l in surrounding_lines):
                changes['components'].append(file)
                changes['semantic_changes'][file].append(f'add {class_name} model')
            else:
                changes['features'].append(file)
                changes['semantic_changes'][file].append(f'add {class_name} class')
    
    # Analyze configuration context
    for i, line in enumerate(context_lines):
        if any(keyword in line.lower() for keyword in ['config', 'settings', 'env']):
            surrounding_lines = context_lines[max(0, i-2):min(len(context_lines), i+3)]
            if any('test' in l.lower() for l in surrounding_lines):
                changes['tests'].append(file)
                changes['semantic_changes'][file].append('add test configuration')
            elif any('security' in l.lower() or 'auth' in l.lower() for l in surrounding_lines):
                changes['security'].append(file)
                changes['semantic_changes'][file].append('add security configuration')
            else:
                changes['config'].append(file)
                changes['semantic_changes'][file].append('add configuration')
    
    # Analyze dependency context
    for i, line in enumerate(context_lines):
        if any(keyword in line.lower() for keyword in ['import ', 'from ', 'require']):
            surrounding_lines = context_lines[max(0, i-2):min(len(context_lines), i+3)]
            if any('test' in l.lower() for l in surrounding_lines):
                changes['tests'].append(file)
                changes['semantic_changes'][file].append('add test dependencies')
            else:
                changes['dependencies'].append(file)
                changes['semantic_changes'][file].append('add dependencies')
    
    # Analyze test context
    for i, line in enumerate(context_lines):
        if any(keyword in line.lower() for keyword in ['test_', 'assert', 'pytest', 'unittest']):
            surrounding_lines = context_lines[max(0, i-2):min(len(context_lines), i+3)]
            if any('mock' in l.lower() or 'patch' in l.lower() for l in surrounding_lines):
                changes['tests'].append(file)
                changes['semantic_changes'][file].append('add mock tests')
            else:
                changes['tests'].append(file)
                changes['semantic_changes'][file].append('add tests')
    
    # Analyze documentation context
    for i, line in enumerate(context_lines):
        if any(keyword in line.lower() for keyword in ['"""', "'''", '#', 'docstring']):
            surrounding_lines = context_lines[max(0, i-2):min(len(context_lines), i+3)]
            if any('api' in l.lower() or 'endpoint' in l.lower() for l in surrounding_lines):
                changes['docs'].append(file)
                changes['semantic_changes'][file].append('add API documentation')
            else:
                changes['docs'].append(file)
                changes['semantic_changes'][file].append('add documentation')

def analyze_code_with_ai(code: str) -> Dict:
    """Analyze code using AI models."""
    try:
        # Use Hugging Face model
        result = code_analyzer(code)
        return {
            'type': result[0]['label'],
            'confidence': result[0]['score']
        }
    except:
        # Fallback to rule-based analysis
        return analyze_code_with_rules(code)

def analyze_code_with_rules(code: str) -> Dict:
    """Analyze code using rule-based approach."""
    analysis = {
        'type': 'chore',
        'confidence': 0.8
    }
    
    # Check for feature additions
    if re.search(r'def\s+\w+\s*\(', code) or re.search(r'class\s+\w+', code):
        # Count new functions and classes
        new_functions = len(re.findall(r'def\s+\w+\s*\(', code))
        new_classes = len(re.findall(r'class\s+\w+', code))
        if new_functions + new_classes > 2:  # If adding multiple new components
            analysis['type'] = 'feat'
        else:
            analysis['type'] = 'refactor'
    
    # Check for bug fixes
    if re.search(r'fix|bug|error|exception', code, re.IGNORECASE):
        analysis['type'] = 'fix'
    
    # Check for documentation
    if re.search(r'"""|docstring|#', code):
        analysis['type'] = 'docs'
    
    # Check for style changes
    if re.search(r'style|format|indent', code, re.IGNORECASE):
        analysis['type'] = 'style'
    
    # Check for refactoring
    if re.search(r'refactor|cleanup|optimize|improve|enhance', code, re.IGNORECASE):
        analysis['type'] = 'refactor'
    
    # Check for tests - only if test-related code is the main change
    test_patterns = r'test_|assert|pytest|unittest'
    if re.search(test_patterns, code):
        # Count test-related lines vs total lines
        test_lines = len(re.findall(test_patterns, code))
        total_lines = len(code.split('\n'))
        if test_lines / total_lines > 0.5:  # If more than 50% of changes are test-related
            analysis['type'] = 'test'
    
    # Check for configuration changes
    if re.search(r'config|settings|env|\.env|\.json|\.yaml|\.yml', code, re.IGNORECASE):
        analysis['type'] = 'chore'
    
    # Check for dependency changes
    if re.search(r'requirements\.txt|package\.json|setup\.py|pipfile', code, re.IGNORECASE):
        analysis['type'] = 'chore'
    
    # Check for build/CI changes
    if re.search(r'build|ci|github|gitlab|travis|circleci|docker', code, re.IGNORECASE):
        analysis['type'] = 'ci'
    
    return analysis

def generate_commit_message(changes: Dict, file_changes: Dict) -> str:
    """Generate commit message using AI analysis."""
    # Analyze changes with AI
    all_code = '\n'.join(changes['added_lines'])
    ai_analysis = analyze_code_with_ai(all_code)
    
    # Determine commit type
    commit_type = ai_analysis['type']
    
    # Determine scope
    scope = None
    if file_changes['modified_files']:
        # Use the most common directory as scope
        dirs = [os.path.dirname(f) for f in file_changes['modified_files']]
        if dirs:
            scope = max(set(dirs), key=dirs.count)
    
    # Generate description
    description = generate_description(changes, file_changes)
    
    # Generate body
    body = generate_body(changes, file_changes)
    
    # Construct commit message
    message = f"{commit_type}"
    if scope:
        message += f"({scope})"
    message += f": {description}"
    
    if body:
        message += f"\n\n{body}"
    
    return message

def generate_description(changes: Dict, file_changes: Dict) -> str:
    """Generate commit description."""
    desc_parts = []
    
    # Add file operations
    if file_changes['added_files']:
        desc_parts.append(f"add {', '.join(file_changes['added_files'])}")
    if file_changes['deleted_files']:
        desc_parts.append(f"remove {', '.join(file_changes['deleted_files'])}")
    if file_changes['renamed_files']:
        desc_parts.append(f"rename {', '.join(f'{old} → {new}' for old, new in file_changes['renamed_files'])}")
    
    # Add content changes
    if changes['security']:
        desc_parts.append("enhance security")
    if changes['features']:
        desc_parts.append("add new features")
    if changes['fixes']:
        desc_parts.append("fix issues")
    if changes['refactors']:
        desc_parts.append("refactor code")
    if changes['performance']:
        desc_parts.append("improve performance")
    if changes['tests']:
        desc_parts.append("update tests")
    if changes['docs']:
        desc_parts.append("update documentation")
    if changes['config']:
        desc_parts.append("update configuration")
    
    return '; '.join(desc_parts)

def generate_body(changes: Dict, file_changes: Dict) -> str:
    """Generate commit body with detailed changes."""
    body_parts = []
    
    # Add detailed changes
    if changes['semantic_changes']:
        body_parts.append("Detailed changes:")
        for file, changes_list in changes['semantic_changes'].items():
            body_parts.append(f"- {file}:")
            for change in sorted(set(changes_list)):
                body_parts.append(f"  - {change}")
    
    # Add metrics
    metrics = changes['code_metrics']
    if metrics['lines_added'] + metrics['lines_removed'] > 0:
        body_parts.append("\nMetrics:")
        body_parts.append(f"- Files changed: {metrics['files_changed']}")
        body_parts.append(f"- Lines added: {metrics['lines_added']}")
        body_parts.append(f"- Lines removed: {metrics['lines_removed']}")
        if metrics['functions_added'] > 0:
            body_parts.append(f"- Functions added: {metrics['functions_added']}")
        if metrics['functions_modified'] > 0:
            body_parts.append(f"- Functions modified: {metrics['functions_modified']}")
        if metrics['classes_added'] > 0:
            body_parts.append(f"- Classes added: {metrics['classes_added']}")
        if metrics['classes_modified'] > 0:
            body_parts.append(f"- Classes modified: {metrics['classes_modified']}")
    
    return '\n'.join(body_parts)

def main():
    try:
        # Get the git diff and original content
        diff, original_content = get_git_diff()
        if not diff:
            console.print("[yellow]No staged changes found. Please stage your changes first.[/yellow]")
            return
        
        # Analyze changes
        console.print("[green]Analyzing changes with AI...[/green]")
        file_changes = analyze_file_changes(diff)
        code_changes = analyze_diff_changes(diff.split('\n'), original_content)
        
        # Generate commit message
        commit_message = generate_commit_message(code_changes, file_changes)
        
        # Show analysis report
        console.print("\n[bold cyan]📊 Change Analysis Report[/bold cyan]")
        console.print("[bold cyan]=" * 50 + "[/bold cyan]")
        
        # Show suggested commit message
        console.print("\n[bold]💡 Suggested Commit Message[/bold]")
        console.print("[bold cyan]-" * 30 + "[/bold cyan]")
        console.print(f"[bold cyan]{commit_message}[/bold cyan]")
        console.print("[bold cyan]=" * 50 + "[/bold cyan]")
        
        # Ask for confirmation
        confirm = Prompt.ask("\nDo you want to use this commit message?", choices=["y", "n"], default="y")
        
        if confirm.lower() == "y":
            repo = Repo('.')
            repo.git.commit("-m", commit_message)
            console.print("[green]Changes committed successfully![/green]")
        else:
            console.print("[yellow]Commit cancelled.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    main() 