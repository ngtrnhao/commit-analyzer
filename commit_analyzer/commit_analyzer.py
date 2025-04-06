import os
from git import Repo
from rich.console import Console
from rich.prompt import Prompt
import re
import ast
from typing import Dict, Set, List, Optional, Tuple
from difflib import unified_diff
import json

console = Console()

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

def analyze_diff_changes(diff_lines: List[str], original_content: Dict[str, str]) -> Dict:
    """Analyze the changes between original and modified files."""
    changes = {
        'functions': set(),
        'classes': set(),
        'imports': set(),
        'variables': set(),
        'tests': set(),
        'styles': set(),
        'docs': set(),
        'components': set(),
        'dependencies': set(),
        'scripts': set(),
        'added_lines': set(),
        'removed_lines': set(),
        'security': set(),
        'features': set(),
        'fixes': set(),
        'refactors': set(),
        'performance': set()
    }
    
    current_file = None
    current_hunk = []
    
    for line in diff_lines:
        line = line.strip()
        if line.startswith('+++ b/'):
            current_file = line[6:]
            current_hunk = []
            continue
            
        if not line or line.startswith('---'):
            continue
            
        if line.startswith('@@'):
            # Process previous hunk
            if current_hunk and current_file:
                analyze_hunk_changes(current_hunk, current_file, original_content.get(current_file, ''), changes)
            current_hunk = []
            continue
            
        current_hunk.append(line)
        
        # Track added/removed lines
        if line.startswith('+'):
            changes['added_lines'].add(line[1:])
        elif line.startswith('-'):
            changes['removed_lines'].add(line[1:])
    
    # Process last hunk
    if current_hunk and current_file:
        analyze_hunk_changes(current_hunk, current_file, original_content.get(current_file, ''), changes)
    
    return changes

def analyze_hunk_changes(hunk: List[str], file_path: str, original_content: str, changes: Dict):
    """Analyze changes in a specific hunk of a file."""
    if file_path.endswith('.py'):
        analyze_python_hunk(hunk, file_path, original_content, changes)
    elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
        analyze_js_hunk(hunk, file_path, original_content, changes)
    elif file_path == 'package.json':
        analyze_package_json_hunk(hunk, file_path, original_content, changes)

def analyze_code_semantics(content: str, file_type: str) -> Dict:
    """Analyze code semantics to understand the purpose and impact of changes."""
    analysis = {
        'features': set(),
        'fixes': set(),
        'refactors': set(),
        'security': set(),
        'performance': set(),
        'tests': set(),
        'docs': set()
    }
    
    # Common patterns for different types of changes
    patterns = {
        'features': [
            r'add\w*',
            r'create\w*',
            r'new\w*',
            r'implement\w*',
            r'feature\w*'
        ],
        'fixes': [
            r'fix\w*',
            r'bug\w*',
            r'error\w*',
            r'issue\w*',
            r'correct\w*'
        ],
        'refactors': [
            r'refactor\w*',
            r'optimize\w*',
            r'improve\w*',
            r'clean\w*',
            r'reorganize\w*'
        ],
        'security': [
            r'security\w*',
            r'vulnerability\w*',
            r'protect\w*',
            r'secure\w*',
            r'authenticate\w*'
        ],
        'performance': [
            r'performance\w*',
            r'speed\w*',
            r'optimize\w*',
            r'efficient\w*',
            r'fast\w*'
        ],
        'tests': [
            r'test\w*',
            r'verify\w*',
            r'validate\w*',
            r'check\w*',
            r'assert\w*'
        ],
        'docs': [
            r'doc\w*',
            r'comment\w*',
            r'explain\w*',
            r'describe\w*',
            r'note\w*'
        ]
    }
    
    # Analyze based on file type
    if file_type == 'py':
        # Parse Python AST
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Analyze function name and docstring
                    func_name = node.name.lower()
                    docstring = ast.get_docstring(node)
                    if docstring:
                        content += f"\n{docstring}"
                    
                    # Check function name patterns
                    for category, category_patterns in patterns.items():
                        if any(re.search(pattern, func_name) for pattern in category_patterns):
                            analysis[category].add(node.name)
                elif isinstance(node, ast.ClassDef):
                    # Analyze class name and docstring
                    class_name = node.name.lower()
                    docstring = ast.get_docstring(node)
                    if docstring:
                        content += f"\n{docstring}"
                    
                    # Check class name patterns
                    for category, category_patterns in patterns.items():
                        if any(re.search(pattern, class_name) for pattern in category_patterns):
                            analysis[category].add(node.name)
        except:
            pass
    elif file_type in ['js', 'jsx', 'ts', 'tsx']:
        # Analyze JavaScript/TypeScript
        for category, category_patterns in patterns.items():
            for pattern in category_patterns:
                matches = re.finditer(pattern, content.lower())
                for match in matches:
                    # Get the context around the match
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end]
                    analysis[category].add(context.strip())
    
    # Analyze comments and docstrings
    for category, category_patterns in patterns.items():
        for pattern in category_patterns:
            matches = re.finditer(pattern, content.lower())
            for match in matches:
                # Get the context around the match
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                analysis[category].add(context.strip())
    
    return analysis

def analyze_python_hunk(hunk: List[str], file_path: str, original_content: str, changes: Dict):
    """Analyze changes in a Python file hunk."""
    try:
        # Parse original content
        original_tree = ast.parse(original_content) if original_content else None
        original_funcs = set()
        original_classes = set()
        original_imports = set()
        if original_tree:
            for node in ast.walk(original_tree):
                if isinstance(node, ast.FunctionDef):
                    original_funcs.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    original_classes.add(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for name in node.names:
                        original_imports.add(name.name)
        
        # Parse modified content
        modified_content = '\n'.join(line[1:] for line in hunk if line.startswith('+'))
        modified_tree = ast.parse(modified_content) if modified_content else None
        if modified_tree:
            for node in ast.walk(modified_tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name not in original_funcs:
                        changes['functions'].add(node.name)
                        # Analyze function semantics
                        semantics = analyze_code_semantics(modified_content, 'py')
                        for category, items in semantics.items():
                            if items:
                                changes[category].add(node.name)
                elif isinstance(node, ast.ClassDef):
                    if node.name not in original_classes:
                        changes['classes'].add(node.name)
                        # Analyze class semantics
                        semantics = analyze_code_semantics(modified_content, 'py')
                        for category, items in semantics.items():
                            if items:
                                changes[category].add(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for name in node.names:
                        if name.name not in original_imports:
                            changes['imports'].add(name.name)
    except Exception as e:
        console.print(f"[red]Error analyzing Python hunk in {file_path}: {str(e)}[/red]")

def analyze_js_hunk(hunk: List[str], file_path: str, original_content: str, changes: Dict):
    """Analyze changes in a JavaScript file hunk."""
    try:
        # Extract functions and classes from original content
        original_funcs = set(re.findall(r'function\s+(\w+)\s*\(', original_content))
        original_classes = set(re.findall(r'class\s+(\w+)\s*{', original_content))
        original_imports = set(re.findall(r'import\s+.*?from\s+[\'"](.*?)[\'"]', original_content))
        
        # Extract functions and classes from modified content
        modified_content = '\n'.join(line[1:] for line in hunk if line.startswith('+'))
        modified_funcs = set(re.findall(r'function\s+(\w+)\s*\(', modified_content))
        modified_classes = set(re.findall(r'class\s+(\w+)\s*{', modified_content))
        modified_imports = set(re.findall(r'import\s+.*?from\s+[\'"](.*?)[\'"]', modified_content))
        
        # Find new functions and classes
        new_funcs = modified_funcs - original_funcs
        new_classes = modified_classes - original_classes
        new_imports = modified_imports - original_imports
        
        changes['functions'].update(new_funcs)
        changes['classes'].update(new_classes)
        changes['imports'].update(new_imports)
        
        # Analyze semantics of new functions and classes
        if new_funcs or new_classes:
            semantics = analyze_code_semantics(modified_content, 'js')
            for category, items in semantics.items():
                if items:
                    changes[category].update(new_funcs | new_classes)
        
        # Extract React components
        components = set(re.findall(r'const\s+(\w+)\s*=\s*\(\)\s*=>\s*{', modified_content))
        changes['components'].update(components)
    except Exception as e:
        console.print(f"[red]Error analyzing JS hunk in {file_path}: {str(e)}[/red]")

def analyze_package_json_hunk(hunk: List[str], file_path: str, original_content: str, changes: Dict):
    """Analyze changes in package.json hunk."""
    try:
        # Parse original content
        original_data = {}
        if original_content:
            try:
                original_data = json.loads(original_content)
            except:
                pass
        
        # Parse modified content
        modified_content = '\n'.join(line[1:] for line in hunk if line.startswith('+'))
        modified_data = {}
        try:
            modified_data = json.loads(modified_content)
        except:
            pass
        
        # Compare dependencies
        if 'dependencies' in modified_data:
            original_deps = original_data.get('dependencies', {})
            modified_deps = modified_data['dependencies']
            for dep, version in modified_deps.items():
                if dep not in original_deps or original_deps[dep] != version:
                    changes['dependencies'].add(f"{dep}@{version}")
        
        # Compare devDependencies
        if 'devDependencies' in modified_data:
            original_dev_deps = original_data.get('devDependencies', {})
            modified_dev_deps = modified_data['devDependencies']
            for dep, version in modified_dev_deps.items():
                if dep not in original_dev_deps or original_dev_deps[dep] != version:
                    changes['dependencies'].add(f"{dep}@{version}")
        
        # Compare scripts
        if 'scripts' in modified_data:
            original_scripts = original_data.get('scripts', {})
            modified_scripts = modified_data['scripts']
            for script, command in modified_scripts.items():
                if script not in original_scripts or original_scripts[script] != command:
                    changes['scripts'].add(script)
    except Exception as e:
        console.print(f"[red]Error analyzing package.json hunk: {str(e)}[/red]")

def analyze_file_changes(diff: str) -> Dict:
    """Analyze what kind of files were changed."""
    files_changed = [line[6:] for line in diff.split('\n') if line.startswith('+++ b/')]
    
    # Analyze file types and content
    file_info = {
        'files': files_changed,
        'has_docs': False,
        'has_tests': False,
        'has_styles': False,
        'components': set(),
        'modules': set(),
        'dependencies': set(),
        'scripts': set()
    }
    
    for file in files_changed:
        # Check file types
        if file.endswith(('.md', '.txt', '.rst', '.doc', '.docx')):
            file_info['has_docs'] = True
        elif 'test' in file.lower() or 'spec' in file.lower():
            file_info['has_tests'] = True
        elif file.endswith(('.css', '.scss', '.less', '.sass', '.style')):
            file_info['has_styles'] = True
        elif file == 'package.json':
            analysis = analyze_package_json(file)
            file_info['dependencies'].update(analysis['dependencies'])
            file_info['dependencies'].update(analysis['dev_dependencies'])
            file_info['scripts'].update(analysis['scripts'])
            
        # Analyze project structure
        parts = file.split('/')
        if 'components' in parts:
            idx = parts.index('components')
            if idx + 1 < len(parts):
                file_info['components'].add(parts[idx + 1])
        elif 'modules' in parts:
            idx = parts.index('modules')
            if idx + 1 < len(parts):
                file_info['modules'].add(parts[idx + 1])
    
    return file_info

def generate_commit_type(changes: Dict, file_changes: Dict) -> str:
    """Generate commit type based on changes."""
    if changes['security']:
        return 'security'
    elif changes['fixes']:
        return 'fix'
    elif changes['features']:
        return 'feat'
    elif changes['refactors']:
        return 'refactor'
    elif changes['performance']:
        return 'perf'
    elif file_changes['has_docs'] or changes['docs']:
        return 'docs'
    elif file_changes['has_tests'] or changes['tests']:
        return 'test'
    elif file_changes['has_styles']:
        return 'style'
    elif changes['dependencies']:
        return 'deps'
    elif changes['scripts']:
        return 'chore'
    return 'chore'

def generate_commit_scope(changes: Dict, file_changes: Dict) -> Optional[str]:
    """Generate commit scope based on changes."""
    # Check for component changes
    if file_changes['components']:
        return next(iter(file_changes['components']))
    # Check for module changes
    elif file_changes['modules']:
        return next(iter(file_changes['modules']))
    # Check for common directory
    elif file_changes['files']:
        dirs = [os.path.dirname(f).split('/')[0] for f in file_changes['files']]
        common_dirs = set(dirs)
        if len(common_dirs) == 1:
            return list(common_dirs)[0]
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

def generate_detailed_commit_description(changes: Dict, file_changes: Dict) -> str:
    """Generate a detailed commit description based on the changes."""
    desc_parts = []
    
    # Handle setup.py specific changes
    if 'setup.py' in file_changes['files']:
        setup_changes = analyze_file_content_changes(
            'setup.py',
            file_changes.get('original_content', ''),
            file_changes.get('modified_content', '')
        )
        
        if setup_changes['metadata']:
            desc_parts.append("update project metadata")
        if setup_changes['dependencies']:
            desc_parts.append("refine dependencies")
        if setup_changes['entry_points']:
            desc_parts.append("enhance entry points")
        if setup_changes['descriptions']:
            desc_parts.append("improve project descriptions")
        if setup_changes['classifiers']:
            desc_parts.append("update package classifiers")
        if setup_changes['other']:
            desc_parts.append("refine setup configuration")
    
    # Handle other file changes
    if changes['security']:
        items = sorted(changes['security'])
        if len(items) == 1:
            desc_parts.append(f"fix security issue in {items[0]}")
        else:
            desc_parts.append(f"fix security issues in {', '.join(items)}")
    
    if changes['features']:
        items = sorted(changes['features'])
        if len(items) == 1:
            desc_parts.append(f"add {items[0]}")
        else:
            desc_parts.append(f"add features: {', '.join(items)}")
    
    if changes['fixes']:
        items = sorted(changes['fixes'])
        if len(items) == 1:
            desc_parts.append(f"fix {items[0]}")
        else:
            desc_parts.append(f"fix issues: {', '.join(items)}")
    
    if changes['refactors']:
        items = sorted(changes['refactors'])
        if len(items) == 1:
            desc_parts.append(f"refactor {items[0]}")
        else:
            desc_parts.append(f"refactor: {', '.join(items)}")
    
    if changes['performance']:
        items = sorted(changes['performance'])
        if len(items) == 1:
            desc_parts.append(f"improve performance of {items[0]}")
        else:
            desc_parts.append(f"improve performance: {', '.join(items)}")
    
    if changes['components']:
        items = sorted(changes['components'])
        if len(items) == 1:
            desc_parts.append(f"update {items[0]} component")
        else:
            desc_parts.append(f"update components: {', '.join(items)}")
    
    if changes['dependencies']:
        items = sorted(changes['dependencies'])
        if len(items) == 1:
            desc_parts.append(f"update {items[0]}")
        else:
            desc_parts.append(f"update dependencies: {', '.join(items)}")
    
    if changes['scripts']:
        items = sorted(changes['scripts'])
        if len(items) == 1:
            desc_parts.append(f"update {items[0]} script")
        else:
            desc_parts.append(f"update scripts: {', '.join(items)}")
    
    # If no specific changes detected, use file names
    if not desc_parts and file_changes['files']:
        files = [os.path.basename(f) for f in file_changes['files']]
        desc_parts.append(f"modify {', '.join(files)}")
    
    return ' and '.join(desc_parts) or "update code"

def analyze_changes(diff: str, original_content: Dict[str, str]) -> Optional[str]:
    """Analyze the changes to generate a commit message."""
    if not diff:
        return "No changes to commit"
    
    try:
        # Analyze file and code changes
        file_changes = analyze_file_changes(diff)
        code_changes = analyze_diff_changes(diff.split('\n'), original_content)
        
        # Store original and modified content for detailed analysis
        for file in file_changes['files']:
            if file in original_content:
                file_changes['original_content'] = original_content[file]
                # Get modified content from diff
                modified_lines = []
                for line in diff.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        modified_lines.append(line[1:])
                file_changes['modified_content'] = '\n'.join(modified_lines)
        
        # Generate commit parts
        commit_type = generate_commit_type(code_changes, file_changes)
        commit_scope = generate_commit_scope(code_changes, file_changes)
        commit_desc = generate_detailed_commit_description(code_changes, file_changes)
        
        # Construct commit message
        message = commit_type
        if commit_scope:
            message += f"({commit_scope})"
        message += f": {commit_desc}"
        
        # Show analysis details
        console.print("\n[bold blue]Change Analysis:[/bold blue]")
        if code_changes['security']:
            console.print(f"[red]Security changes:[/red] {', '.join(code_changes['security'])}")
        if code_changes['features']:
            console.print(f"[green]Features added:[/green] {', '.join(code_changes['features'])}")
        if code_changes['fixes']:
            console.print(f"[yellow]Fixes:[/yellow] {', '.join(code_changes['fixes'])}")
        if code_changes['refactors']:
            console.print(f"[cyan]Refactors:[/cyan] {', '.join(code_changes['refactors'])}")
        if code_changes['performance']:
            console.print(f"[magenta]Performance improvements:[/magenta] {', '.join(code_changes['performance'])}")
        if code_changes['components']:
            console.print(f"[green]Components changed:[/green] {', '.join(code_changes['components'])}")
        if code_changes['dependencies']:
            console.print(f"[blue]Dependencies changed:[/blue] {', '.join(code_changes['dependencies'])}")
        if code_changes['scripts']:
            console.print(f"[yellow]Scripts changed:[/yellow] {', '.join(code_changes['scripts'])}")
        
        # Show added/removed lines summary
        if code_changes['added_lines'] or code_changes['removed_lines']:
            console.print("\n[bold blue]Code Changes Summary:[/bold blue]")
            console.print(f"[green]Lines added:[/green] {len(code_changes['added_lines'])}")
            console.print(f"[red]Lines removed:[/red] {len(code_changes['removed_lines'])}")
        
        return message
    except Exception as e:
        console.print(f"[red]Error generating commit message: {str(e)}[/red]")
        return None

def main():
    try:
        # Get the git diff and original content
        diff, original_content = get_git_diff()
        if not diff:
            console.print("[yellow]No staged changes found. Please stage your changes first.[/yellow]")
            return
        
        # Generate commit message
        console.print("[green]Analyzing changes...[/green]")
        commit_message = analyze_changes(diff, original_content)
        
        if commit_message:
            console.print("\n[bold]Suggested commit message:[/bold]")
            console.print(f"[cyan]{commit_message}[/cyan]")
            
            # Ask for confirmation
            confirm = Prompt.ask("\nDo you want to use this commit message?", choices=["y", "n"], default="y")
            
            if confirm.lower() == "y":
                repo = Repo('.')
                repo.git.commit("-m", commit_message)
                console.print("[green]Changes committed successfully![/green]")
            else:
                console.print("[yellow]Commit cancelled.[/yellow]")
        else:
            console.print("[red]Failed to generate commit message.[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

if __name__ == "__main__":
    main() 