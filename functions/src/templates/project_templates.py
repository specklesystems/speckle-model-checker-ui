def get_project_selection_template():
    """
    Return HTML template for project selection screen.
    """
    return '''
    <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-6">Select a Speckle Project</h2>
        
        <div class="htmx-indicator flex justify-center mb-4">
            <svg class="animate-spin h-8 w-8 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
        </div>
        
        {% if projects %}
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {% for project in projects %}
                    <div class="border border-gray-200 rounded p-4 hover:shadow-md transition-shadow">
                        <h3 class="font-medium text-lg mb-2">{{ project.name }}</h3>
                        
                        {% if project.description %}
                            <p class="text-gray-600 text-sm mb-4 line-clamp-2">{{ project.description }}</p>
                        {% else %}
                            <p class="text-gray-500 text-sm italic mb-4">No description</p>
                        {% endif %}
                        
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-gray-500">Updated: {{ project.updatedAt|date }}</span>
                            <button 
                                class="px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary-dark"
                                hx-get="/api/projects/{{ project.id }}"
                                hx-target="#main-content"
                                hx-indicator=".htmx-indicator">
                                Select
                            </button>
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% else %}
            <div class="text-center py-10 bg-gray-50 rounded border border-gray-200">
                <svg class="w-16 h-16 text-gray-400 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <p class="text-gray-500 mb-4">You don't have any Speckle projects yet.</p>
                <a href="https://app.speckle.systems/" target="_blank" class="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark">
                    Create a Project on Speckle
                </a>
            </div>
        {% endif %}
        
        <div class="mt-6 pt-4 border-t border-gray-200 flex justify-between items-center">
            <button
                class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                onclick="window.location.reload()">
                Refresh Projects
            </button>
            
            <a href="https://app.speckle.systems/" target="_blank" class="text-primary hover:underline text-sm">
                Open Speckle Web App
            </a>
        </div>
    </div>
    '''

def get_project_details_template():
    """
    Return HTML template for project details with rulesets.
    """
    return '''
    <div class="bg-white rounded-lg shadow p-6">
        <div class="flex justify-between items-center mb-6">
            <div>
                <h2 class="text-xl font-semibold">{{ project.name }}</h2>
                {% if project.description %}
                    <p class="text-gray-600">{{ project.description }}</p>
                {% endif %}
            </div>
            
            <button
                class="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                hx-get="/api/projects"
                hx-target="#main-content">
                Back to Projects
            </button>
        </div>
        
        <div class="mb-8">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-medium">Rule Sets</h3>
                <button
                    class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center"
                    hx-get="/api/rulesets/new?projectId={{ project.id }}"
                    hx-target="#main-content">
                    <span class="htmx-indicator mr-2">
                        <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                        </svg>
                    </span>
                    Create New Rule Set
                </button>
            </div>
            
            {% if rulesets %}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="ruleset-container">
                    {% for ruleset in rulesets %}
                        <div id="ruleset-card-{{ ruleset.id }}" class="bg-white rounded-lg shadow p-4 border border-gray-200">
                            <div class="flex justify-between items-start mb-3">
                                <h4 class="text-lg font-semibold text-foreground">{{ ruleset.name }}</h4>
                                <div class="flex space-x-1">
                                    <button class="p-1 text-gray-500 hover:text-gray-700" 
                                        hx-get="/api/rulesets/{{ ruleset.id }}/edit" 
                                        hx-target="#main-content" 
                                        hx-trigger="click" 
                                        title="Edit Rule Set">
                                        <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                        </svg>
                                    </button>
                                    <button class="p-1 text-gray-500 hover:text-red-700" 
                                        hx-delete="/api/rulesets/{{ ruleset.id }}" 
                                        hx-confirm="Are you sure you want to delete this rule set?" 
                                        hx-target="#ruleset-card-{{ ruleset.id }}" 
                                        hx-swap="outerHTML" 
                                        title="Delete Rule Set">
                                        <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                            <polyline points="3 6 5 6 21 6"></polyline>
                                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                            <line x1="10" y1="11" x2="10" y2="17"></line>
                                            <line x1="14" y1="11" x2="14" y2="17"></line>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                            <div class="text-sm text-secondary mb-3">
                                <p>Last updated: {{ ruleset.updated_at }}</p>
                                <p>{{ ruleset.rule_count }} rules</p>
                                
                                {% if ruleset.isShared %}
                                    <p class="text-green-600 text-xs mt-1">
                                        <svg class="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                                        </svg>
                                        Publicly shared
                                    </p>
                                {% endif %}
                            </div>
                            <div class="flex flex-col space-y-2">
                                <a href="/shared/{{ ruleset.id }}" class="text-xs text-gray-500 truncate hover:text-gray-700 mb-2">
                                    {{ window.location.origin }}/shared/{{ ruleset.id }}
                                    <svg class="w-4 h-4 inline-block ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                                    </svg>
                                </a>
                                <div class="flex space-x-2">
                                    <button class="px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary-dark"
                                        hx-get="/api/rulesets/{{ ruleset.id }}/edit" 
                                        hx-target="#main-content">
                                        Edit Rules
                                    </button>
                                    <button class="px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700"
                                        hx-get="/api/rulesets/{{ ruleset.id }}/share" 
                                        hx-target="#share-dialog-container" 
                                        hx-trigger="click">
                                        Share
                                    </button>
                                    <button class="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                                        hx-get="/api/rulesets/{{ ruleset.id }}/export" 
                                        hx-trigger="click">
                                        Export
                                    </button>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="text-center py-10 bg-gray-50 rounded border border-gray-200">
                    <p class="text-gray-500 mb-4">No rule sets defined for this project yet.</p>
                    <button
                        class="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
                        hx-get="/api/rulesets/new?projectId={{ project.id }}"
                        hx-target="#main-content">
                        Create Your First Rule Set
                    </button>
                </div>
            {% endif %}
        </div>
        
        {% if project.models and project.models.items %}
        <div>
            <h3 class="text-lg font-medium mb-3">Available Models</h3>
            <div class="bg-gray-50 p-4 rounded border border-gray-200">
                <ul class="space-y-2">
                    {% for model in project.models.items %}
                        <li class="flex justify-between items-center">
                            <div>
                                <span class="font-medium">{{ model.name }}</span>
                                {% if model.description %}
                                    <p class="text-sm text-gray-600">{{ model.description }}</p>
                                {% endif %}
                            </div>
                            <a 
                                href="https://app.speckle.systems/streams/{{ model.id }}" 
                                target="_blank"
                                class="text-primary hover:underline text-sm">
                                View in Speckle
                            </a>
                        </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
        
        <div class="mt-8 pt-6 border-t border-gray-200">
            <div class="flex justify-between items-center">
                <div>
                    <h4 class="text-sm font-medium">Project Collaborators</h4>
                    <div class="flex items-center mt-2">
                        {% for collaborator in project.collaborators %}
                            <div class="flex items-center mr-4" title="{{ collaborator.user.name }} ({{ collaborator.role }})">
                                <img src="{{ collaborator.user.avatar or 'https://via.placeholder.com/32' }}" 
                                    alt="{{ collaborator.user.name }}" 
                                    class="w-8 h-8 rounded-full border border-gray-200">
                            </div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="text-sm text-gray-500">
                    <p>Created: {{ project.createdAt|date }}</p>
                    <p>Updated: {{ project.updatedAt|date }}</p>
                </div>
            </div>
        </div>
    </div>
    '''

def get_new_ruleset_form_template():
    """
    Return HTML template for creating a new ruleset.
    """
    return '''
    <div class="bg-white rounded-lg shadow p-6 max-w-2xl mx-auto">
        <h2 class="text-xl font-semibold mb-4">Create New Rule Set for {{ project_name }}</h2>
        
        <form hx-post="/api/rulesets" 
            hx-target="#main-content" 
            hx-swap="outerHTML" 
            class="space-y-4">
            
            <input type="hidden" name="projectId" value="{{ project_id }}">
            
            <div>
                <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Rule Set Name</label>
                <input type="text" id="name" name="name" 
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary focus:border-primary"
                    required>
            </div>
            
            <div>
                <label for="description" class="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
                <textarea id="description" name="description" rows="3"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary focus:border-primary"></textarea>
            </div>
            
            <div class="flex justify-between">
                <button type="button" 
                    class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                    hx-get="/api/projects/{{ project_id }}" 
                    hx-target="#main-content">
                    Cancel
                </button>
                <button type="submit" 
                    class="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark">
                    Create Rule Set
                </button>
            </div>
        </form>
    </div>
    '''