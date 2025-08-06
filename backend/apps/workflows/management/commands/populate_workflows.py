from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.workflows.models import NodeType, WorkflowTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate workflow node types and templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-templates',
            action='store_true',
            help='Skip creating workflow templates, only create node types',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting workflow population...'))
        
        # Create node types
        self.create_node_types()
        
        # Create workflow templates if not skipped
        if not options['skip_templates']:
            self.create_workflow_templates()
        
        self.stdout.write(self.style.SUCCESS('Workflow population completed!'))

    def create_node_types(self):
        """Create basic node types for workflow builder."""
        node_types_data = [
            {
                'name': 'Start',
                'type': 'start',
                'icon': 'play-circle',
                'color': '#28a745',
                'description': 'Starting point of the workflow',
                'config_schema': {
                    'trigger_type': {
                        'type': 'select',
                        'options': ['manual', 'schedule', 'webhook', 'document_upload'],
                        'default': 'manual'
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': True
            },
            {
                'name': 'End',
                'type': 'end',
                'icon': 'stop-circle',
                'color': '#dc3545',
                'description': 'End point of the workflow',
                'config_schema': {
                    'success_message': {
                        'type': 'text',
                        'default': 'Workflow completed successfully'
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': False
            },
            {
                'name': 'Document Processing',
                'type': 'document',
                'icon': 'file-text',
                'color': '#007bff',
                'description': 'Process documents using AI OCR and extraction',
                'config_schema': {
                    'document_types': {
                        'type': 'multiselect',
                        'options': ['invoice', 'contract', 'receipt', 'form'],
                        'default': ['invoice']
                    },
                    'confidence_threshold': {
                        'type': 'slider',
                        'min': 0.5,
                        'max': 1.0,
                        'step': 0.1,
                        'default': 0.8
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': True
            },
            {
                'name': 'Human Approval',
                'type': 'approval',
                'icon': 'check-circle',
                'color': '#ffc107',
                'description': 'Require human approval before proceeding',
                'config_schema': {
                    'approvers': {
                        'type': 'user_select',
                        'multiple': True
                    },
                    'approval_message': {
                        'type': 'textarea',
                        'default': 'Please review and approve this workflow step'
                    },
                    'timeout_hours': {
                        'type': 'number',
                        'default': 24,
                        'min': 1,
                        'max': 168
                    }
                },
                'requires_user_action': True,
                'allows_multiple_outputs': True
            },
            {
                'name': 'Decision',
                'type': 'decision',
                'icon': 'git-branch',
                'color': '#6f42c1',
                'description': 'Branch workflow based on conditions',
                'config_schema': {
                    'conditions': {
                        'type': 'condition_builder',
                        'fields': ['amount', 'document_type', 'confidence_score', 'custom_field']
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': True
            },
            {
                'name': 'Data Processing',
                'type': 'process',
                'icon': 'cpu',
                'color': '#17a2b8',
                'description': 'Process and transform data',
                'config_schema': {
                    'processing_type': {
                        'type': 'select',
                        'options': ['validate', 'transform', 'calculate', 'format'],
                        'default': 'validate'
                    },
                    'validation_rules': {
                        'type': 'json_editor'
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': True
            },
            {
                'name': 'Email Notification',
                'type': 'notification',
                'icon': 'mail',
                'color': '#fd7e14',
                'description': 'Send email notifications',
                'config_schema': {
                    'recipients': {
                        'type': 'email_list'
                    },
                    'subject': {
                        'type': 'text',
                        'default': 'Workflow Notification'
                    },
                    'template': {
                        'type': 'template_select'
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': True
            },
            {
                'name': 'CRM Integration',
                'type': 'integration',
                'icon': 'link',
                'color': '#20c997',
                'description': 'Integrate with CRM systems',
                'config_schema': {
                    'crm_system': {
                        'type': 'select',
                        'options': ['salesforce', 'hubspot', 'pipedrive', 'custom'],
                        'default': 'salesforce'
                    },
                    'action': {
                        'type': 'select',
                        'options': ['create_contact', 'update_contact', 'create_opportunity', 'update_deal'],
                        'default': 'create_contact'
                    },
                    'field_mapping': {
                        'type': 'field_mapper'
                    }
                },
                'requires_user_action': False,
                'allows_multiple_outputs': True
            }
        ]

        created_count = 0
        for node_data in node_types_data:
            node_type, created = NodeType.objects.get_or_create(
                name=node_data['name'],
                type=node_data['type'],
                defaults=node_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created node type: {node_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} new node types')
        )

    def create_workflow_templates(self):
        """Create pre-built workflow templates."""
        templates_data = [
            {
                'name': 'Invoice Processing Workflow',
                'description': 'Automated invoice processing with AI extraction and approval workflow',
                'category': 'document_processing',
                'complexity_level': 2,
                'setup_time_minutes': 15,
                'tags': ['invoice', 'finance', 'approval', 'automation'],
                'definition': {
                    'nodes': [
                        {
                            'node_id': 'start_1',
                            'name': 'Receive Invoice',
                            'type': 'start',
                            'position': {'x': 100, 'y': 100},
                            'config': {'trigger_type': 'document_upload'}
                        },
                        {
                            'node_id': 'process_1',
                            'name': 'Extract Invoice Data',
                            'type': 'document',
                            'position': {'x': 300, 'y': 100},
                            'config': {
                                'document_types': ['invoice'],
                                'confidence_threshold': 0.85
                            }
                        },
                        {
                            'node_id': 'decision_1',
                            'name': 'Amount Check',
                            'type': 'decision',
                            'position': {'x': 500, 'y': 100},
                            'config': {
                                'conditions': [
                                    {'field': 'amount', 'operator': '>', 'value': 1000}
                                ]
                            }
                        },
                        {
                            'node_id': 'approval_1',
                            'name': 'Manager Approval',
                            'type': 'approval',
                            'position': {'x': 700, 'y': 50},
                            'config': {
                                'approval_message': 'High-value invoice requires approval',
                                'timeout_hours': 48
                            }
                        },
                        {
                            'node_id': 'integration_1',
                            'name': 'Update Accounting System',
                            'type': 'integration',
                            'position': {'x': 700, 'y': 150},
                            'config': {
                                'crm_system': 'custom',
                                'action': 'create_invoice_record'
                            }
                        },
                        {
                            'node_id': 'end_1',
                            'name': 'Complete',
                            'type': 'end',
                            'position': {'x': 900, 'y': 100},
                            'config': {'success_message': 'Invoice processed successfully'}
                        }
                    ],
                    'edges': [
                        {'source': 'start_1', 'target': 'process_1', 'condition_type': 'always'},
                        {'source': 'process_1', 'target': 'decision_1', 'condition_type': 'success'},
                        {'source': 'decision_1', 'target': 'approval_1', 'condition_type': 'conditional', 'label': 'Amount > $1000'},
                        {'source': 'decision_1', 'target': 'integration_1', 'condition_type': 'conditional', 'label': 'Amount ≤ $1000'},
                        {'source': 'approval_1', 'target': 'integration_1', 'condition_type': 'approval_yes'},
                        {'source': 'integration_1', 'target': 'end_1', 'condition_type': 'success'}
                    ]
                }
            },
            {
                'name': 'Customer Onboarding Workflow',
                'description': 'Streamlined customer onboarding process with document collection and CRM integration',
                'category': 'customer_service',
                'complexity_level': 3,
                'setup_time_minutes': 25,
                'tags': ['onboarding', 'customer', 'crm', 'documents'],
                'definition': {
                    'nodes': [
                        {
                            'node_id': 'start_1',
                            'name': 'New Customer Sign-up',
                            'type': 'start',
                            'position': {'x': 100, 'y': 150},
                            'config': {'trigger_type': 'webhook'}
                        },
                        {
                            'node_id': 'integration_1',
                            'name': 'Create CRM Contact',
                            'type': 'integration',
                            'position': {'x': 300, 'y': 150},
                            'config': {
                                'crm_system': 'salesforce',
                                'action': 'create_contact'
                            }
                        },
                        {
                            'node_id': 'notification_1',
                            'name': 'Welcome Email',
                            'type': 'notification',
                            'position': {'x': 500, 'y': 100},
                            'config': {
                                'subject': 'Welcome to our platform!',
                                'template': 'welcome_email'
                            }
                        },
                        {
                            'node_id': 'document_1',
                            'name': 'Process KYC Documents',
                            'type': 'document',
                            'position': {'x': 500, 'y': 200},
                            'config': {
                                'document_types': ['id', 'address_proof'],
                                'confidence_threshold': 0.9
                            }
                        },
                        {
                            'node_id': 'approval_1',
                            'name': 'KYC Review',
                            'type': 'approval',
                            'position': {'x': 700, 'y': 200},
                            'config': {
                                'approval_message': 'Please review customer KYC documents',
                                'timeout_hours': 72
                            }
                        },
                        {
                            'node_id': 'notification_2',
                            'name': 'Account Activation',
                            'type': 'notification',
                            'position': {'x': 900, 'y': 150},
                            'config': {
                                'subject': 'Account Activated Successfully',
                                'template': 'account_activated'
                            }
                        },
                        {
                            'node_id': 'end_1',
                            'name': 'Onboarding Complete',
                            'type': 'end',
                            'position': {'x': 1100, 'y': 150},
                            'config': {'success_message': 'Customer successfully onboarded'}
                        }
                    ],
                    'edges': [
                        {'source': 'start_1', 'target': 'integration_1', 'condition_type': 'always'},
                        {'source': 'integration_1', 'target': 'notification_1', 'condition_type': 'success'},
                        {'source': 'integration_1', 'target': 'document_1', 'condition_type': 'success'},
                        {'source': 'document_1', 'target': 'approval_1', 'condition_type': 'success'},
                        {'source': 'approval_1', 'target': 'notification_2', 'condition_type': 'approval_yes'},
                        {'source': 'notification_2', 'target': 'end_1', 'condition_type': 'success'}
                    ]
                }
            },
            {
                'name': 'Contract Review and Approval',
                'description': 'Legal contract review workflow with multi-stage approvals',
                'category': 'approval',
                'complexity_level': 4,
                'setup_time_minutes': 30,
                'tags': ['contract', 'legal', 'approval', 'compliance'],
                'definition': {
                    'nodes': [
                        {
                            'node_id': 'start_1',
                            'name': 'Contract Submitted',
                            'type': 'start',
                            'position': {'x': 100, 'y': 200},
                            'config': {'trigger_type': 'document_upload'}
                        },
                        {
                            'node_id': 'document_1',
                            'name': 'Extract Contract Terms',
                            'type': 'document',
                            'position': {'x': 300, 'y': 200},
                            'config': {
                                'document_types': ['contract'],
                                'confidence_threshold': 0.75
                            }
                        },
                        {
                            'node_id': 'decision_1',
                            'name': 'Contract Value Check',
                            'type': 'decision',
                            'position': {'x': 500, 'y': 200},
                            'config': {
                                'conditions': [
                                    {'field': 'contract_value', 'operator': '>', 'value': 50000}
                                ]
                            }
                        },
                        {
                            'node_id': 'approval_1',
                            'name': 'Legal Team Review',
                            'type': 'approval',
                            'position': {'x': 700, 'y': 150},
                            'config': {
                                'approval_message': 'Please review contract terms and clauses',
                                'timeout_hours': 120
                            }
                        },
                        {
                            'node_id': 'approval_2',
                            'name': 'Executive Approval',
                            'type': 'approval',
                            'position': {'x': 700, 'y': 250},
                            'config': {
                                'approval_message': 'High-value contract requires executive approval',
                                'timeout_hours': 168
                            }
                        },
                        {
                            'node_id': 'notification_1',
                            'name': 'Contract Approved Notification',
                            'type': 'notification',
                            'position': {'x': 900, 'y': 200},
                            'config': {
                                'subject': 'Contract Approved and Ready for Signing',
                                'template': 'contract_approved'
                            }
                        },
                        {
                            'node_id': 'end_1',
                            'name': 'Ready for Execution',
                            'type': 'end',
                            'position': {'x': 1100, 'y': 200},
                            'config': {'success_message': 'Contract approved and ready for execution'}
                        }
                    ],
                    'edges': [
                        {'source': 'start_1', 'target': 'document_1', 'condition_type': 'always'},
                        {'source': 'document_1', 'target': 'decision_1', 'condition_type': 'success'},
                        {'source': 'decision_1', 'target': 'approval_1', 'condition_type': 'always'},
                        {'source': 'decision_1', 'target': 'approval_2', 'condition_type': 'conditional', 'label': 'Value > $50K'},
                        {'source': 'approval_1', 'target': 'notification_1', 'condition_type': 'approval_yes'},
                        {'source': 'approval_2', 'target': 'notification_1', 'condition_type': 'approval_yes'},
                        {'source': 'notification_1', 'target': 'end_1', 'condition_type': 'success'}
                    ]
                }
            },
            {
                'name': 'Expense Report Processing',
                'description': 'Automated expense report processing with receipt validation and approval',
                'category': 'document_processing',
                'complexity_level': 2,
                'setup_time_minutes': 20,
                'tags': ['expense', 'receipt', 'approval', 'finance'],
                'definition': {
                    'nodes': [
                        {
                            'node_id': 'start_1',
                            'name': 'Expense Report Submitted',
                            'type': 'start',
                            'position': {'x': 100, 'y': 150},
                            'config': {'trigger_type': 'manual'}
                        },
                        {
                            'node_id': 'document_1',
                            'name': 'Process Receipts',
                            'type': 'document',
                            'position': {'x': 300, 'y': 150},
                            'config': {
                                'document_types': ['receipt'],
                                'confidence_threshold': 0.8
                            }
                        },
                        {
                            'node_id': 'process_1',
                            'name': 'Validate Expenses',
                            'type': 'process',
                            'position': {'x': 500, 'y': 150},
                            'config': {
                                'processing_type': 'validate',
                                'validation_rules': {
                                    'max_meal_amount': 50,
                                    'max_daily_total': 200
                                }
                            }
                        },
                        {
                            'node_id': 'decision_1',
                            'name': 'Amount Validation',
                            'type': 'decision',
                            'position': {'x': 700, 'y': 150},
                            'config': {
                                'conditions': [
                                    {'field': 'total_amount', 'operator': '>', 'value': 500}
                                ]
                            }
                        },
                        {
                            'node_id': 'approval_1',
                            'name': 'Manager Approval',
                            'type': 'approval',
                            'position': {'x': 900, 'y': 100},
                            'config': {
                                'approval_message': 'Please approve this expense report',
                                'timeout_hours': 48
                            }
                        },
                        {
                            'node_id': 'integration_1',
                            'name': 'Process Payment',
                            'type': 'integration',
                            'position': {'x': 900, 'y': 200},
                            'config': {
                                'crm_system': 'custom',
                                'action': 'create_payment_request'
                            }
                        },
                        {
                            'node_id': 'end_1',
                            'name': 'Expense Processed',
                            'type': 'end',
                            'position': {'x': 1100, 'y': 150},
                            'config': {'success_message': 'Expense report processed successfully'}
                        }
                    ],
                    'edges': [
                        {'source': 'start_1', 'target': 'document_1', 'condition_type': 'always'},
                        {'source': 'document_1', 'target': 'process_1', 'condition_type': 'success'},
                        {'source': 'process_1', 'target': 'decision_1', 'condition_type': 'success'},
                        {'source': 'decision_1', 'target': 'approval_1', 'condition_type': 'conditional', 'label': 'Amount > $500'},
                        {'source': 'decision_1', 'target': 'integration_1', 'condition_type': 'conditional', 'label': 'Amount ≤ $500'},
                        {'source': 'approval_1', 'target': 'integration_1', 'condition_type': 'approval_yes'},
                        {'source': 'integration_1', 'target': 'end_1', 'condition_type': 'success'}
                    ]
                }
            },
            {
                'name': 'Support Ticket Routing',
                'description': 'Intelligent support ticket routing based on content analysis and urgency',
                'category': 'customer_service',
                'complexity_level': 3,
                'setup_time_minutes': 25,
                'tags': ['support', 'ticketing', 'ai', 'routing'],
                'definition': {
                    'nodes': [
                        {
                            'node_id': 'start_1',
                            'name': 'New Support Ticket',
                            'type': 'start',
                            'position': {'x': 100, 'y': 200},
                            'config': {'trigger_type': 'webhook'}
                        },
                        {
                            'node_id': 'process_1',
                            'name': 'Analyze Ticket Content',
                            'type': 'process',
                            'position': {'x': 300, 'y': 200},
                            'config': {
                                'processing_type': 'ai_analysis',
                                'analysis_type': 'sentiment_and_category'
                            }
                        },
                        {
                            'node_id': 'decision_1',
                            'name': 'Urgency Check',
                            'type': 'decision',
                            'position': {'x': 500, 'y': 200},
                            'config': {
                                'conditions': [
                                    {'field': 'urgency', 'operator': '==', 'value': 'high'},
                                    {'field': 'category', 'operator': 'in', 'value': ['billing', 'security']}
                                ]
                            }
                        },
                        {
                            'node_id': 'notification_1',
                            'name': 'Priority Alert',
                            'type': 'notification',
                            'position': {'x': 700, 'y': 100},
                            'config': {
                                'subject': 'High Priority Support Ticket',
                                'template': 'priority_alert'
                            }
                        },
                        {
                            'node_id': 'integration_1',
                            'name': 'Route to Specialist',
                            'type': 'integration',
                            'position': {'x': 700, 'y': 200},
                            'config': {
                                'crm_system': 'custom',
                                'action': 'assign_to_specialist_queue'
                            }
                        },
                        {
                            'node_id': 'integration_2',
                            'name': 'Route to General Queue',
                            'type': 'integration',
                            'position': {'x': 700, 'y': 300},
                            'config': {
                                'crm_system': 'custom',
                                'action': 'assign_to_general_queue'
                            }
                        },
                        {
                            'node_id': 'end_1',
                            'name': 'Ticket Routed',
                            'type': 'end',
                            'position': {'x': 900, 'y': 200},
                            'config': {'success_message': 'Support ticket routed successfully'}
                        }
                    ],
                    'edges': [
                        {'source': 'start_1', 'target': 'process_1', 'condition_type': 'always'},
                        {'source': 'process_1', 'target': 'decision_1', 'condition_type': 'success'},
                        {'source': 'decision_1', 'target': 'notification_1', 'condition_type': 'conditional', 'label': 'High Priority'},
                        {'source': 'decision_1', 'target': 'integration_1', 'condition_type': 'conditional', 'label': 'Specialist Required'},
                        {'source': 'decision_1', 'target': 'integration_2', 'condition_type': 'conditional', 'label': 'General Queue'},
                        {'source': 'notification_1', 'target': 'integration_1', 'condition_type': 'success'},
                        {'source': 'integration_1', 'target': 'end_1', 'condition_type': 'success'},
                        {'source': 'integration_2', 'target': 'end_1', 'condition_type': 'success'}
                    ]
                }
            }
        ]

        created_count = 0
        for template_data in templates_data:
            template, created = WorkflowTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created workflow template: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} new workflow templates')
        )