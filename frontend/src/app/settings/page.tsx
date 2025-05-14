'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

type AIStyle = {
  id: string;
  name: string;
  description: string;
  example: string;
  isDefault?: boolean;
};

type IntegrationStatus = {
  service: string;
  connected: boolean;
  accountInfo?: string;
  lastSync?: string;
};

export default function SettingsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('general');
  const [theme, setTheme] = useState('dark');
  const [aiStyles, setAiStyles] = useState<AIStyle[]>([]);
  const [defaultAiStyle, setDefaultAiStyle] = useState('professional');
  const [autoSaveInterval, setAutoSaveInterval] = useState(60);
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  
  // Fetch settings when component mounts
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        // In a real app, this would call your API
        // const response = await fetch('/api/settings');
        // const data = await response.json();
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Sample AI styles
        const stylesData: AIStyle[] = [
          {
            id: 'professional',
            name: 'Professional',
            description: 'Clear, concise, and formal writing suitable for business or academic books',
            example: 'The methodology employed in this study adheres to established research protocols.',
            isDefault: true
          },
          {
            id: 'conversational',
            name: 'Conversational',
            description: 'Friendly and approachable tone that speaks directly to the reader',
            example: 'Let me tell you why this approach works so well in everyday situations.',
          },
          {
            id: 'academic',
            name: 'Academic',
            description: 'Scholarly writing with formal structure and specialized vocabulary',
            example: 'The empirical evidence suggests a strong correlation between variables X and Y.',
          },
          {
            id: 'storytelling',
            name: 'Storytelling',
            description: 'Narrative style with descriptive language and engaging flow',
            example: 'The morning sun cast long shadows as Maria began her unexpected journey.',
          },
          {
            id: 'technical',
            name: 'Technical',
            description: 'Precise, detailed explanations for technical subjects',
            example: 'The function accepts three parameters and returns a boolean value indicating success.',
          }
        ];
        
        // Sample integrations
        const integrationsData: IntegrationStatus[] = [
          {
            service: 'Google Drive',
            connected: true,
            accountInfo: 'user@example.com',
            lastSync: '2025-05-12T10:30:00Z'
          },
          {
            service: 'Dropbox',
            connected: false
          },
          {
            service: 'Microsoft OneDrive',
            connected: false
          },
          {
            service: 'Grammarly',
            connected: true,
            accountInfo: 'user@example.com',
            lastSync: '2025-05-11T15:45:00Z'
          },
          {
            service: 'Scrivener',
            connected: false
          }
        ];
        
        setAiStyles(stylesData);
        setDefaultAiStyle('professional');
        setTheme('dark');
        setAutoSaveInterval(60);
        setIntegrations(integrationsData);
      } catch (error) {
        console.error('Error fetching settings:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchSettings();
  }, []);
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const handleSave = async () => {
    setIsSaving(true);
    
    try {
      // In a real app, this would call your API
      // const response = await fetch('/api/settings', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     theme,
      //     defaultAiStyle,
      //     autoSaveInterval
      //   })
      // });
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Show success message or notification here
    } catch (error) {
      console.error('Error saving settings:', error);
      // Show error message
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleConnect = async (service: string) => {
    // In a real app, this would redirect to OAuth flow
    console.log(`Connecting to ${service}...`);
    
    // Simulate connection
    setIntegrations(prev => 
      prev.map(integration => 
        integration.service === service
          ? { 
              ...integration, 
              connected: true,
              accountInfo: 'user@example.com',
              lastSync: new Date().toISOString()
            }
          : integration
      )
    );
  };
  
  const handleDisconnect = async (service: string) => {
    // In a real app, this would revoke OAuth tokens
    console.log(`Disconnecting from ${service}...`);
    
    // Simulate disconnection
    setIntegrations(prev => 
      prev.map(integration => 
        integration.service === service
          ? { 
              ...integration, 
              connected: false,
              accountInfo: undefined,
              lastSync: undefined
            }
          : integration
      )
    );
  };

  if (isLoading) {
    return (
      <div className="container mx-auto flex-1 p-6 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="text-zinc-400">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <h1 className="text-3xl font-bold text-zinc-100 mb-6">Settings</h1>
      
      <div className="flex flex-col md:flex-row gap-6">
        {/* Settings Navigation */}
        <div className="w-full md:w-64 shrink-0">
          <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 sticky top-24">
            <nav>
              <ul className="space-y-1">
                <li>
                  <button
                    onClick={() => setActiveTab('general')}
                    className={`w-full text-left px-4 py-2 rounded-md ${
                      activeTab === 'general'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-300 hover:bg-zinc-700'
                    }`}
                  >
                    General
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('aiStyles')}
                    className={`w-full text-left px-4 py-2 rounded-md ${
                      activeTab === 'aiStyles'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-300 hover:bg-zinc-700'
                    }`}
                  >
                    AI Writing Styles
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('integrations')}
                    className={`w-full text-left px-4 py-2 rounded-md ${
                      activeTab === 'integrations'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-300 hover:bg-zinc-700'
                    }`}
                  >
                    Integrations
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('notifications')}
                    className={`w-full text-left px-4 py-2 rounded-md ${
                      activeTab === 'notifications'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-300 hover:bg-zinc-700'
                    }`}
                  >
                    Notifications
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveTab('backup')}
                    className={`w-full text-left px-4 py-2 rounded-md ${
                      activeTab === 'backup'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-300 hover:bg-zinc-700'
                    }`}
                  >
                    Backup & Recovery
                  </button>
                </li>
              </ul>
            </nav>
          </div>
        </div>
        
        {/* Settings Content */}
        <div className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg p-6">
          {/* General Settings */}
          {activeTab === 'general' && (
            <div>
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">General Settings</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-zinc-300 mb-2">Theme</label>
                  <div className="flex gap-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        value="light"
                        checked={theme === 'light'}
                        onChange={() => setTheme('light')}
                        className="mr-2"
                      />
                      <span className="text-zinc-300">Light</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        value="dark"
                        checked={theme === 'dark'}
                        onChange={() => setTheme('dark')}
                        className="mr-2"
                      />
                      <span className="text-zinc-300">Dark</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="theme"
                        value="system"
                        checked={theme === 'system'}
                        onChange={() => setTheme('system')}
                        className="mr-2"
                      />
                      <span className="text-zinc-300">System Default</span>
                    </label>
                  </div>
                </div>
                
                <div>
                  <label className="block text-zinc-300 mb-2">Auto-Save Interval (seconds)</label>
                  <select
                    value={autoSaveInterval}
                    onChange={(e) => setAutoSaveInterval(parseInt(e.target.value))}
                    className="bg-zinc-700 border border-zinc-600 rounded-md px-3 py-2 text-zinc-200 w-full max-w-xs"
                  >
                    <option value="30">30 seconds</option>
                    <option value="60">1 minute</option>
                    <option value="300">5 minutes</option>
                    <option value="600">10 minutes</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-zinc-300 mb-2">Default Editor View</label>
                  <select
                    className="bg-zinc-700 border border-zinc-600 rounded-md px-3 py-2 text-zinc-200 w-full max-w-xs"
                  >
                    <option value="rich">Rich Text</option>
                    <option value="split">Split View</option>
                    <option value="markdown">Markdown</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-zinc-300 mb-2">Language</label>
                  <select
                    className="bg-zinc-700 border border-zinc-600 rounded-md px-3 py-2 text-zinc-200 w-full max-w-xs"
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="zh">Chinese</option>
                  </select>
                </div>
              </div>
            </div>
          )}
          
          {/* AI Writing Styles */}
          {activeTab === 'aiStyles' && (
            <div>
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">AI Writing Styles</h2>
              <p className="text-zinc-400 mb-6">
                Select your preferred default AI writing style for content generation.
                This can be overridden on a per-book or per-chapter basis.
              </p>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-zinc-300 mb-2">Default Writing Style</label>
                  <div className="space-y-3">
                    {aiStyles.map(style => (
                      <div 
                        key={style.id}
                        className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                          defaultAiStyle === style.id
                            ? 'border-indigo-500 bg-indigo-900/20'
                            : 'border-zinc-700 hover:bg-zinc-700/50'
                        }`}
                        onClick={() => setDefaultAiStyle(style.id)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-medium text-zinc-200">{style.name}</h3>
                          <div className={`w-4 h-4 rounded-full ${defaultAiStyle === style.id ? 'bg-indigo-500' : 'bg-zinc-700'}`}></div>
                        </div>
                        <p className="text-zinc-400 text-sm mb-3">{style.description}</p>
                        <div className="bg-zinc-900 rounded p-3 text-zinc-300 text-sm italic">
                          "{style.example}"
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                    Create Custom Style
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Integrations */}
          {activeTab === 'integrations' && (
            <div>
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Integrations</h2>
              <p className="text-zinc-400 mb-6">
                Connect Auto Author with other services to extend your workflow.
              </p>
              
              <div className="space-y-4">
                {integrations.map(integration => (
                  <div 
                    key={integration.service}
                    className="border border-zinc-700 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-zinc-200">{integration.service}</h3>
                        {integration.connected && integration.accountInfo && (
                          <div className="text-zinc-400 text-sm mt-1">
                            Connected as {integration.accountInfo}
                            {integration.lastSync && (
                              <span className="block mt-1">Last synced: {formatDate(integration.lastSync)}</span>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {integration.connected ? (
                        <button 
                          onClick={() => handleDisconnect(integration.service)}
                          className="px-3 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md text-sm"
                        >
                          Disconnect
                        </button>
                      ) : (
                        <button 
                          onClick={() => handleConnect(integration.service)}
                          className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm"
                        >
                          Connect
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Notifications */}
          {activeTab === 'notifications' && (
            <div>
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Notification Settings</h2>
              
              <div className="space-y-4">
                <div className="border-b border-zinc-700 pb-4">
                  <label className="flex items-center justify-between">
                    <span className="text-zinc-300">Email Notifications</span>
                    <span className="relative inline-block w-10 h-6 transition duration-200 ease-in-out bg-zinc-700 rounded-full">
                      <input 
                        type="checkbox"
                        className="absolute w-6 h-6 transition duration-200 ease-in-out transform bg-white rounded-full appearance-none cursor-pointer peer checked:translate-x-4 checked:bg-indigo-600"
                      />
                      <span className="absolute inset-0 transition duration-200 ease-in-out bg-zinc-700 rounded-full peer-checked:bg-indigo-900"></span>
                    </span>
                  </label>
                  <p className="text-zinc-400 text-sm mt-1">
                    Receive email notifications about collaborative changes and updates
                  </p>
                </div>
                
                <div className="border-b border-zinc-700 pb-4">
                  <label className="flex items-center justify-between">
                    <span className="text-zinc-300">Browser Notifications</span>
                    <span className="relative inline-block w-10 h-6 transition duration-200 ease-in-out bg-zinc-700 rounded-full">
                      <input 
                        type="checkbox" 
                        defaultChecked
                        className="absolute w-6 h-6 transition duration-200 ease-in-out transform bg-white rounded-full appearance-none cursor-pointer peer checked:translate-x-4 checked:bg-indigo-600"
                      />
                      <span className="absolute inset-0 transition duration-200 ease-in-out bg-zinc-700 rounded-full peer-checked:bg-indigo-900"></span>
                    </span>
                  </label>
                  <p className="text-zinc-400 text-sm mt-1">
                    Show browser notifications for important events
                  </p>
                </div>
                
                <div className="border-b border-zinc-700 pb-4">
                  <label className="flex items-center justify-between">
                    <span className="text-zinc-300">Writing Reminders</span>
                    <span className="relative inline-block w-10 h-6 transition duration-200 ease-in-out bg-zinc-700 rounded-full">
                      <input 
                        type="checkbox" 
                        defaultChecked
                        className="absolute w-6 h-6 transition duration-200 ease-in-out transform bg-white rounded-full appearance-none cursor-pointer peer checked:translate-x-4 checked:bg-indigo-600"
                      />
                      <span className="absolute inset-0 transition duration-200 ease-in-out bg-zinc-700 rounded-full peer-checked:bg-indigo-900"></span>
                    </span>
                  </label>
                  <p className="text-zinc-400 text-sm mt-1">
                    Get reminders to maintain your writing streak
                  </p>
                </div>
                
                <div className="border-b border-zinc-700 pb-4">
                  <label className="flex items-center justify-between">
                    <span className="text-zinc-300">Product Updates</span>
                    <span className="relative inline-block w-10 h-6 transition duration-200 ease-in-out bg-zinc-700 rounded-full">
                      <input 
                        type="checkbox"
                        className="absolute w-6 h-6 transition duration-200 ease-in-out transform bg-white rounded-full appearance-none cursor-pointer peer checked:translate-x-4 checked:bg-indigo-600"
                      />
                      <span className="absolute inset-0 transition duration-200 ease-in-out bg-zinc-700 rounded-full peer-checked:bg-indigo-900"></span>
                    </span>
                  </label>
                  <p className="text-zinc-400 text-sm mt-1">
                    Receive notifications about new features and improvements
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Backup & Recovery */}
          {activeTab === 'backup' && (
            <div>
              <h2 className="text-xl font-semibold text-zinc-100 mb-4">Backup & Recovery</h2>
              
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-zinc-200 mb-2">Automatic Backups</h3>
                  <p className="text-zinc-400 mb-4">
                    Configure how often your books are automatically backed up to the cloud.
                  </p>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-zinc-300 mb-2">Backup Frequency</label>
                      <select
                        className="bg-zinc-700 border border-zinc-600 rounded-md px-3 py-2 text-zinc-200 w-full max-w-xs"
                      >
                        <option value="daily">Daily</option>
                        <option value="hourly">Hourly</option>
                        <option value="realtime">Real-time</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-zinc-300 mb-2">Version History</label>
                      <select
                        className="bg-zinc-700 border border-zinc-600 rounded-md px-3 py-2 text-zinc-200 w-full max-w-xs"
                      >
                        <option value="10">Keep last 10 versions</option>
                        <option value="30">Keep last 30 versions</option>
                        <option value="90">Keep last 90 versions</option>
                        <option value="unlimited">Keep unlimited versions</option>
                      </select>
                    </div>
                  </div>
                </div>
                
                <div className="border-t border-zinc-700 pt-6">
                  <h3 className="text-lg font-medium text-zinc-200 mb-2">Manual Backup</h3>
                  <p className="text-zinc-400 mb-4">
                    Create a backup of all your books and content right now.
                  </p>
                  
                  <div className="flex gap-4">
                    <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md">
                      Create Backup
                    </button>
                    <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 font-medium rounded-md">
                      Download Backup
                    </button>
                  </div>
                </div>
                
                <div className="border-t border-zinc-700 pt-6">
                  <h3 className="text-lg font-medium text-zinc-200 mb-2">Restore from Backup</h3>
                  <p className="text-zinc-400 mb-4">
                    Restore your content from a previous backup.
                  </p>
                  
                  <div className="flex gap-4">
                    <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 font-medium rounded-md">
                      Choose Backup File
                    </button>
                    <button className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 font-medium rounded-md">
                      Restore
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Save Button */}
          <div className="mt-8 pt-4 border-t border-zinc-700">
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
