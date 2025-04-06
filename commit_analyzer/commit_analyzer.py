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

def analyze_code_structure(file_path: str, content: str) -> Dict:
    """Analyze the structure and patterns in code files."""
    analysis = {
        'imports': set(),
        'functions': set(),
        'classes': set(),
        'variables': set(),
        'patterns': set()
    }
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        
        # Analyze imports
        if line.startswith('import ') or line.startswith('from '):
            analysis['imports'].add(line)
        
        # Analyze function definitions
        if line.startswith('def '):
            func_name = line.split('def ')[1].split('(')[0].strip()
            analysis['functions'].add(func_name)
        
        # Analyze class definitions
        if line.startswith('class '):
            class_name = line.split('class ')[1].split('(')[0].strip()
            analysis['classes'].add(class_name)
        
        # Analyze variable assignments
        if '=' in line and not line.startswith(('#', 'def ', 'class ')):
            var_name = line.split('=')[0].strip()
            if not var_name.startswith((' ', '\t')):
                analysis['variables'].add(var_name)
        
        # Analyze common patterns
        if 'if __name__ == "__main__":' in line:
            analysis['patterns'].add('main block')
        if '@' in line:
            analysis['patterns'].add('decorator')
        if 'try:' in line:
            analysis['patterns'].add('try-except')
        if 'with ' in line:
            analysis['patterns'].add('context manager')
    
    return analysis

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
            current_file = line.split(' ')[2][2:]  # Remove 'a/' prefix
            changes['files'].add(current_file)
            file_ext = os.path.splitext(current_file)[1]
            changes['file_types'][file_ext].add(current_file)
        
        elif line.startswith('new file mode'):
            changes['added_files'].add(current_file)
        
        elif line.startswith('deleted file mode'):
            changes['deleted_files'].add(current_file)
            changes['files'].remove(current_file)
        
        elif line.startswith('rename from'):
            old_file = line.split(' ')[2]
            changes['renamed_files'].add((old_file, current_file))
            changes['files'].remove(old_file)
        
        elif line.startswith('+') and not line.startswith('+++'):
            if current_file:
                changes['content_changes'][current_file]['added'].append(line[1:])
        
        elif line.startswith('-') and not line.startswith('---'):
            if current_file:
                changes['content_changes'][current_file]['removed'].append(line[1:])
    
    # Determine modified files
    changes['modified_files'] = changes['files'] - changes['added_files'] - {f[1] for f in changes['renamed_files']}
    
    return changes

def analyze_diff_changes(diff_lines: List[str], original_content: Dict[str, str]) -> Dict:
    """Analyze code changes with more detailed categorization."""
    changes = {
        'security': set(),
        'features': set(),
        'fixes': set(),
        'refactors': set(),
        'performance': set(),
        'components': set(),
        'dependencies': set(),
        'scripts': set(),
        'tests': set(),
        'docs': set(),
        'config': set(),
        'style': set(),
        'added_lines': [],
        'removed_lines': [],
        'code_metrics': {
            'lines_added': 0,
            'lines_removed': 0,
            'files_changed': 0,
            'complexity_changes': 0
        }
    }
    
    current_file = None
    for line in diff_lines:
        if line.startswith('diff --git'):
            current_file = line.split(' ')[2][2:]
            changes['code_metrics']['files_changed'] += 1
        
        elif line.startswith('+') and not line.startswith('+++'):
            content = line[1:]
            changes['added_lines'].append(content)
            changes['code_metrics']['lines_added'] += 1
            
            if current_file:
                # Enhanced pattern detection
                if any(keyword in content.lower() for keyword in ['password', 'secret', 'key', 'token']):
                    changes['security'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['def ', 'class ', 'async def']):
                    changes['features'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['fix', 'bug', 'error', 'exception']):
                    changes['fixes'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['refactor', 'cleanup', 'optimize']):
                    changes['refactors'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['performance', 'speed', 'efficient']):
                    changes['performance'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['test_', 'assert', 'pytest']):
                    changes['tests'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['"""', "'''", '#']):
                    changes['docs'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['config', 'settings', 'env']):
                    changes['config'].add(current_file)
                elif any(keyword in content.lower() for keyword in ['import ', 'from ', 'require']):
                    changes['dependencies'].add(current_file)
        
        elif line.startswith('-') and not line.startswith('---'):
            content = line[1:]
            changes['removed_lines'].append(content)
            changes['code_metrics']['lines_removed'] += 1
    
    return changes

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
    elif changes['docs']:
        return 'docs'
    elif changes['tests']:
        return 'test'
    elif changes['style']:
        return 'style'
    elif changes['dependencies']:
        return 'deps'
    elif changes['scripts']:
        return 'chore'
    return 'chore'

def generate_commit_scope(changes: Dict, file_changes: Dict) -> Optional[str]:
    """Generate commit scope based on changes."""
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
            
    # If no common scope found, return None
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
    """Generate a detailed commit description based on comprehensive analysis."""
    desc_parts = []
    
    # Handle file operations
    if file_changes['added_files']:
        files = sorted(file_changes['added_files'])
        if len(files) == 1:
            desc_parts.append(f"add new file {files[0]}")
        else:
            desc_parts.append(f"add new files: {', '.join(files)}")
    
    if file_changes['deleted_files']:
        files = sorted(file_changes['deleted_files'])
        if len(files) == 1:
            desc_parts.append(f"remove file {files[0]}")
        else:
            desc_parts.append(f"remove files: {', '.join(files)}")
    
    if file_changes['renamed_files']:
        renames = [f"{old} -> {new}" for old, new in sorted(file_changes['renamed_files'])]
        desc_parts.append(f"rename files: {', '.join(renames)}")
    
    # Handle content changes
    if changes['security']:
        items = sorted(changes['security'])
        desc_parts.append(f"enhance security in {', '.join(items)}")
    
    if changes['features']:
        items = sorted(changes['features'])
        if len(items) == 1:
            desc_parts.append(f"implement new feature in {items[0]}")
        else:
            desc_parts.append(f"implement new features in {', '.join(items)}")
    
    if changes['fixes']:
        items = sorted(changes['fixes'])
        if len(items) == 1:
            desc_parts.append(f"fix issue in {items[0]}")
        else:
            desc_parts.append(f"fix issues in {', '.join(items)}")
    
    if changes['refactors']:
        items = sorted(changes['refactors'])
        if len(items) == 1:
            desc_parts.append(f"refactor code in {items[0]}")
        else:
            desc_parts.append(f"refactor code in {', '.join(items)}")
    
    if changes['performance']:
        items = sorted(changes['performance'])
        if len(items) == 1:
            desc_parts.append(f"optimize performance in {items[0]}")
        else:
            desc_parts.append(f"optimize performance in {', '.join(items)}")
    
    if changes['tests']:
        items = sorted(changes['tests'])
        if len(items) == 1:
            desc_parts.append(f"update tests in {items[0]}")
        else:
            desc_parts.append(f"update tests in {', '.join(items)}")
    
    if changes['docs']:
        items = sorted(changes['docs'])
        if len(items) == 1:
            desc_parts.append(f"update documentation in {items[0]}")
        else:
            desc_parts.append(f"update documentation in {', '.join(items)}")
    
    if changes['config']:
        items = sorted(changes['config'])
        if len(items) == 1:
            desc_parts.append(f"update configuration in {items[0]}")
        else:
            desc_parts.append(f"update configuration in {', '.join(items)}")
    
    if changes['dependencies']:
        items = sorted(changes['dependencies'])
        if len(items) == 1:
            desc_parts.append(f"update dependencies in {items[0]}")
        else:
            desc_parts.append(f"update dependencies in {', '.join(items)}")
    
    # Add code metrics summary if significant changes
    metrics = changes['code_metrics']
    if metrics['lines_added'] + metrics['lines_removed'] > 100:
        desc_parts.append(f"({metrics['lines_added']}+/{metrics['lines_removed']}- lines)")
    
    return ' and '.join(desc_parts) or "update code"

def analyze_changes(diff: str, original_content: Dict[str, str]) -> Optional[str]:
    """Analyze the changes to generate a detailed commit message."""
    if not diff:
        return "No changes to commit"
    
    try:
        # Analyze file and code changes
        file_changes = analyze_file_changes(diff)
        code_changes = analyze_diff_changes(diff.split('\n'), original_content)
        
        # Analyze code structure for modified files
        for file in file_changes['modified_files']:
            if file in original_content:
                structure = analyze_code_structure(file, original_content[file])
                # Use structure analysis to enhance change detection
                if structure['functions']:
                    code_changes['components'].add(file)
        
        # Generate commit parts
        commit_type = generate_commit_type(code_changes, file_changes)
        commit_scope = generate_commit_scope(code_changes, file_changes)
        commit_desc = generate_detailed_commit_description(code_changes, file_changes)
        
        # Construct commit message
        message = commit_type
        if commit_scope:
            message += f"({commit_scope})"
        message += f": {commit_desc}"
        
        # Show detailed analysis
        console.print("\n[bold blue]Detailed Change Analysis:[/bold blue]")
        
        # Show file operations
        if file_changes['added_files'] or file_changes['deleted_files'] or file_changes['renamed_files']:
            console.print("\n[bold]File Operations:[/bold]")
            if file_changes['added_files']:
                console.print(f"[green]Added:[/green] {', '.join(sorted(file_changes['added_files']))}")
            if file_changes['deleted_files']:
                console.print(f"[red]Deleted:[/red] {', '.join(sorted(file_changes['deleted_files']))}")
            if file_changes['renamed_files']:
                console.print(f"[yellow]Renamed:[/yellow] {', '.join(f'{old} -> {new}' for old, new in sorted(file_changes['renamed_files']))}")
        
        # Show content changes
        console.print("\n[bold]Content Changes:[/bold]")
        for category in ['security', 'features', 'fixes', 'refactors', 'performance', 
                        'tests', 'docs', 'config', 'dependencies']:
            if code_changes[category]:
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
                console.print(f"[{color}]{category.title()}:[/{color}] {', '.join(sorted(code_changes[category]))}")
        
        # Show code metrics
        metrics = code_changes['code_metrics']
        console.print("\n[bold]Code Metrics:[/bold]")
        console.print(f"[blue]Files changed:[/blue] {metrics['files_changed']}")
        console.print(f"[green]Lines added:[/green] {metrics['lines_added']}")
        console.print(f"[red]Lines removed:[/red] {metrics['lines_removed']}")
        
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