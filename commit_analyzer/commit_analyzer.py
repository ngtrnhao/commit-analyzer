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
        'feature_details': defaultdict(list),  # Store detailed feature changes
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
    
    for line in diff_lines:
        if line.startswith('diff --git'):
            current_file = line.split(' ')[2][2:]
            changes['code_metrics']['files_changed'] += 1
            current_function = None
            current_class = None
        
        elif line.startswith('+') and not line.startswith('+++'):
            content = line[1:]
            changes['added_lines'].append(content)
            changes['code_metrics']['lines_added'] += 1
            
            if current_file:
                # Enhanced pattern detection with feature details
                if any(keyword in content.lower() for keyword in ['password', 'secret', 'key', 'token', 'auth', 'login']):
                    changes['security'].add(current_file)
                    changes['feature_details'][current_file].append('enhance security')
                
                elif any(keyword in content.lower() for keyword in ['def ', 'class ', 'async def']):
                    if 'def ' in content:
                        changes['code_metrics']['functions_added'] += 1
                        func_name = content.split('def ')[1].split('(')[0].strip()
                        current_function = func_name
                        changes['feature_details'][current_file].append(f'add {func_name} function')
                    elif 'class ' in content:
                        changes['code_metrics']['classes_added'] += 1
                        class_name = content.split('class ')[1].split('(')[0].strip()
                        current_class = class_name
                        changes['feature_details'][current_file].append(f'add {class_name} class')
                    changes['features'].add(current_file)
                
                elif any(keyword in content.lower() for keyword in ['children', 'array', 'list', 'default']):
                    changes['features'].add(current_file)
                    if 'children' in content.lower():
                        changes['feature_details'][current_file].append('enhance children handling')
                    if 'default' in content.lower():
                        changes['feature_details'][current_file].append('add default values')
                
                elif any(keyword in content.lower() for keyword in ['fix', 'bug', 'error', 'exception', 'handle']):
                    changes['fixes'].add(current_file)
                    changes['feature_details'][current_file].append('fix issues')
                
                elif any(keyword in content.lower() for keyword in ['refactor', 'cleanup', 'optimize', 'improve']):
                    changes['refactors'].add(current_file)
                    changes['feature_details'][current_file].append('refactor code')
                
                elif any(keyword in content.lower() for keyword in ['performance', 'speed', 'efficient', 'fast']):
                    changes['performance'].add(current_file)
                    changes['feature_details'][current_file].append('improve performance')
                
                elif any(keyword in content.lower() for keyword in ['test_', 'assert', 'pytest', 'unittest']):
                    changes['tests'].add(current_file)
                    changes['feature_details'][current_file].append('add tests')
                
                elif any(keyword in content.lower() for keyword in ['"""', "'''", '#', 'docstring']):
                    changes['docs'].add(current_file)
                    changes['feature_details'][current_file].append('update documentation')
                
                elif any(keyword in content.lower() for keyword in ['config', 'settings', 'env']):
                    changes['config'].add(current_file)
                    changes['feature_details'][current_file].append('update configuration')
                
                elif any(keyword in content.lower() for keyword in ['import ', 'from ', 'require']):
                    changes['dependencies'].add(current_file)
                    changes['code_metrics']['imports_added'] += 1
                    changes['feature_details'][current_file].append('add dependencies')
                
                elif '.bat' in current_file.lower() or '.sh' in current_file.lower():
                    changes['scripts'].add(current_file)
                    changes['feature_details'][current_file].append('add script')
    
    return changes

def generate_commit_type(changes: Dict, file_changes: Dict) -> str:
    """Generate commit type based on changes."""
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
    return '🔧 chore'

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
    feature_summary = []
    
    # Group changes by type and collect feature details
    script_changes = []
    model_changes = []
    config_changes = []
    other_changes = []
    
    # Process added files first
    if file_changes['added_files']:
        for file in sorted(file_changes['added_files']):
            base_name = os.path.basename(file)
            if '.bat' in file.lower() or '.sh' in file.lower():
                script_changes.append(f"add {base_name} script")
            elif 'model' in file.lower() or 'schema' in file.lower():
                model_changes.append(f"add {base_name} model")
            elif 'config' in file.lower() or 'settings' in file.lower():
                config_changes.append(f"add {base_name} configuration")
            else:
                other_changes.append(f"add {base_name}")
    
    # Process feature details
    for file, details in changes['feature_details'].items():
        base_name = os.path.basename(file)
        if 'model' in file.lower() or 'schema' in file.lower():
            # Combine related model changes
            unique_details = list(set(details))
            if unique_details:
                model_changes.append(f"enhance {base_name} with {', '.join(unique_details)}")
        elif '.bat' in file.lower() or '.sh' in file.lower():
            script_changes.extend(details)
        elif 'config' in file.lower() or 'settings' in file.lower():
            config_changes.extend(details)
        else:
            other_changes.extend(details)
    
    # Combine changes into meaningful groups
    if script_changes:
        feature_summary.append('; '.join(sorted(set(script_changes))))
    if model_changes:
        feature_summary.append('; '.join(sorted(set(model_changes))))
    if config_changes:
        feature_summary.append('; '.join(sorted(set(config_changes))))
    if other_changes:
        feature_summary.append('; '.join(sorted(set(other_changes))))
    
    # Create the main description
    if feature_summary:
        desc_parts.append(' and '.join(feature_summary))
    
    # Add metrics if significant
    metrics = changes['code_metrics']
    if metrics['lines_added'] + metrics['lines_removed'] > 0:
        desc_parts.append(f"({metrics['lines_added']}+/{metrics['lines_removed']}- lines)")
    
    return ' '.join(desc_parts) or "update code"

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
        
        # Show suggested commit message with enhanced styling
        console.print("\n[bold]💡 Suggested Commit Message[/bold]")
        console.print("[bold cyan]-" * 30 + "[/bold cyan]")
        console.print(f"[bold cyan]{message}[/bold cyan]")
        console.print("[bold cyan]=" * 50 + "[/bold cyan]")
        
        return message
    except Exception as e:
        console.print(f"[red]❌ Error generating commit message: {str(e)}[/red]")
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