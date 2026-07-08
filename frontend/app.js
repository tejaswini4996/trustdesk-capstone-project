// Global State
let activeTicketId = null;
let activeRole = 'support_agent';
let activeToken = 'agent-token';
let activeAction = null; // Stores current recommended action details
let evalPollingInterval = null;

// DOM Elements
const tabTickets = document.getElementById('tab-tickets');
const tabEvals = document.getElementById('tab-evals');
const ticketsView = document.getElementById('tickets-view');
const evalsView = document.getElementById('evals-view');
const roleSelect = document.getElementById('role-select');
const ticketListContainer = document.getElementById('ticket-list-container');
const ticketTotalBadge = document.getElementById('ticket-total-badge');

const welcomeScreen = document.getElementById('welcome-screen');
const workspaceLayout = document.getElementById('workspace-layout');

// Active Ticket Elements
const activeTicketIdEl = document.getElementById('active-ticket-id');
const activeTicketSubject = document.getElementById('active-ticket-subject');
const activeTicketChannel = document.getElementById('active-ticket-channel');
const activeTicketDate = document.getElementById('active-ticket-date');
const activeTicketBody = document.getElementById('active-ticket-body');

// Action Buttons
const btnTriage = document.getElementById('btn-triage');
const btnDraft = document.getElementById('btn-draft');

// Triage Output Elements
const triageCard = document.getElementById('triage-card');
const triageCategory = document.getElementById('triage-category');
const triagePriority = document.getElementById('triage-priority');
const triageSentiment = document.getElementById('triage-sentiment');
const triageEscalate = document.getElementById('triage-escalate');
const triageReason = document.getElementById('triage-reason');

// Draft Output Elements
const draftCard = document.getElementById('draft-card');
const draftReplyBody = document.getElementById('draft-reply-body');
const citationsContainer = document.getElementById('citations-container');
const guardrailAlert = document.getElementById('guardrail-alert');
const guardrailStatusText = document.getElementById('guardrail-status-text');

// Action Approvals Panel Elements
const actionPanel = document.getElementById('action-panel');
const actionToolName = document.getElementById('action-tool-name');
const actionStatusBadge = document.getElementById('action-status-badge');
const actionReason = document.getElementById('action-reason');
const actionPayloadPreview = document.getElementById('action-payload-preview');
const btnActionApprove = document.getElementById('btn-action-approve');
const btnActionReject = document.getElementById('btn-action-reject');
const actionAgentMessage = document.getElementById('action-agent-message');

// Context Panel Elements
const customerName = document.getElementById('customer-name');
const customerEmail = document.getElementById('customer-email');
const customerTier = document.getElementById('customer-tier');
const customerVerified = document.getElementById('customer-verified');
const customerCountry = document.getElementById('customer-country');

const orderCard = document.getElementById('order-card');
const orderNotLinkedMsg = document.getElementById('order-not-found-msg');
const orderDetailsContainer = document.getElementById('order-details-container');
const orderIdEl = document.getElementById('order-id');
const orderStatusEl = document.getElementById('order-status');
const orderPaymentEl = document.getElementById('order-payment');
const orderTotalEl = document.getElementById('order-total');
const orderTrackingEl = document.getElementById('order-tracking');
const orderReturnWindowEl = document.getElementById('order-return-window');
const orderItemsContainer = document.getElementById('order-items-container');

// Trace Elements
const traceIdEl = document.getElementById('trace-id');
const traceLogContent = document.getElementById('trace-log-content');

// Modal Elements
const policyModal = document.getElementById('policy-modal');
const policyModalTitle = document.getElementById('policy-modal-title');
const policyModalContent = document.getElementById('policy-modal-content');
const btnClosePolicy = document.getElementById('btn-close-policy');

// Evals Elements
const btnRunEval = document.getElementById('btn-run-eval');
const evalMetricTotal = document.getElementById('eval-metric-total');
const evalMetricCategory = document.getElementById('eval-metric-category');
const evalMetricPriority = document.getElementById('eval-metric-priority');
const evalMetricCitation = document.getElementById('eval-metric-citation');
const evalMetricSafety = document.getElementById('eval-metric-safety');
const evalResultsTbody = document.getElementById('eval-results-tbody');


// INITS & LISTENERS

roleSelect.addEventListener('change', (e) => {
  activeRole = e.target.value;
  if (activeRole === 'support_agent') activeToken = 'agent-token';
  else if (activeRole === 'support_manager') activeToken = 'manager-token';
  else if (activeRole === 'admin') activeToken = 'admin-token';
  
  // Refresh button state permissions visual validation
  updateActionPanelButtons();
});

tabTickets.addEventListener('click', () => {
  tabTickets.classList.add('active');
  tabEvals.classList.remove('active');
  ticketsView.style.display = 'flex';
  evalsView.style.display = 'none';
});

tabEvals.addEventListener('click', () => {
  tabEvals.classList.add('active');
  tabTickets.classList.remove('active');
  ticketsView.style.display = 'none';
  evalsView.style.display = 'block';
  loadEvalResults();
});

// Event Triggers
btnTriage.addEventListener('click', triageTicket);
btnDraft.addEventListener('click', generateDraft);
btnActionApprove.addEventListener('click', () => handleActionApproval(true));
btnActionReject.addEventListener('click', () => handleActionApproval(false));
btnRunEval.addEventListener('click', triggerEvalSuite);
btnClosePolicy.addEventListener('click', () => { policyModal.style.display = 'none'; });

// API HELPER FUNCTIONS
async function apiRequest(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${activeToken}`,
    ...options.headers
  };
  
  const response = await fetch(endpoint, { ...options, headers });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }
  
  return response.json();
}

// 1. Fetch tickets and render queue sidebar
async function loadTickets() {
  try {
    const tickets = await apiRequest('/api/tickets');
    ticketListContainer.innerHTML = '';
    ticketTotalBadge.textContent = tickets.length;
    
    if (tickets.length === 0) {
      ticketListContainer.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No tickets found</div>';
      return;
    }
    
    tickets.forEach(ticket => {
      const item = document.createElement('div');
      item.className = `ticket-item ${activeTicketId === ticket.ticket_id ? 'active' : ''}`;
      item.addEventListener('click', () => selectTicket(ticket.ticket_id));
      
      const priorityClass = `badge-priority-${ticket.expected_priority.toLowerCase()}`;
      
      item.innerHTML = `
        <div class="ticket-item-top">
          <span class="ticket-id">${ticket.ticket_id}</span>
          <span class="badge ${priorityClass}">${ticket.expected_priority}</span>
        </div>
        <div class="ticket-subject">${ticket.subject}</div>
        <div class="badge-row">
          <span class="badge badge-category">${ticket.expected_category}</span>
          <span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-muted);">${ticket.channel}</span>
        </div>
      `;
      ticketListContainer.appendChild(item);
    });
  } catch (err) {
    alert(`Failed to load tickets: ${err.message}`);
  }
}

// 2. Select and display ticket details
async function selectTicket(ticketId) {
  activeTicketId = ticketId;
  
  // Highlight active sidebar item
  const items = document.querySelectorAll('.ticket-item');
  items.forEach(item => {
    const idSpan = item.querySelector('.ticket-id');
    if (idSpan && idSpan.textContent === ticketId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
  
  // Reset Panels
  triageCard.style.display = 'none';
  draftCard.style.display = 'none';
  actionPanel.style.display = 'none';
  actionAgentMessage.style.display = 'none';
  activeAction = null;
  
  // Fetch details
  try {
    const ticket = await apiRequest(`/api/tickets/${ticketId}`);
    const context = await apiRequest(`/api/tickets/${ticketId}/context`);
    
    // Show panels
    welcomeScreen.style.display = 'none';
    workspaceLayout.style.display = 'flex';
    
    // Fill Info
    activeTicketIdEl.textContent = ticket.ticket_id;
    activeTicketSubject.textContent = ticket.subject;
    activeTicketChannel.textContent = ticket.channel;
    activeTicketDate.textContent = new Date(ticket.created_at).toLocaleString();
    activeTicketBody.textContent = ticket.body;
    
    // Customer profile
    customerName.textContent = context.customer.name;
    customerEmail.textContent = context.customer.email;
    customerTier.textContent = context.customer.tier.toUpperCase();
    customerVerified.textContent = context.customer.verified ? 'Verified ✅' : 'Unverified ❌';
    customerVerified.style.color = context.customer.verified ? 'var(--success-color)' : 'var(--danger-color)';
    customerCountry.textContent = context.customer.country;
    
    // Order info
    if (context.order) {
      orderNotLinkedMsg.style.display = 'none';
      orderDetailsContainer.style.display = 'block';
      
      orderIdEl.textContent = context.order.order_id;
      orderStatusEl.textContent = context.order.status.toUpperCase();
      orderPaymentEl.textContent = context.order.payment_status.toUpperCase();
      orderTotalEl.textContent = `${context.order.total} ${context.order.currency}`;
      orderTrackingEl.textContent = context.order.tracking_number || 'N/A';
      orderReturnWindowEl.textContent = context.order.eligible_return_until ? new Date(context.order.eligible_return_until).toLocaleDateString() : 'N/A';
      
      // Items list
      orderItemsContainer.innerHTML = '';
      const items = JSON.parse(context.order.items_json);
      items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'order-item-spec';
        row.innerHTML = `
          <span>${item.name} (${item.sku})</span>
          <span style="color: var(--text-muted);">x${item.quantity}</span>
        `;
        orderItemsContainer.appendChild(row);
      });
    } else {
      orderNotLinkedMsg.style.display = 'block';
      orderDetailsContainer.style.display = 'none';
    }
    
    // Trace init
    traceIdEl.textContent = 'None';
    traceLogContent.textContent = 'No active trace records generated for this ticket yet.';
    
  } catch (err) {
    alert(`Failed to load ticket context: ${err.message}`);
  }
}

// 3. AI Triage execution
async function triageTicket() {
  if (!activeTicketId) return;
  
  btnTriage.disabled = true;
  btnTriage.textContent = 'Analyzing...';
  
  try {
    const triage = await apiRequest(`/api/tickets/${activeTicketId}/triage`, { method: 'POST' });
    
    triageCard.style.display = 'block';
    triageCategory.textContent = triage.category;
    triagePriority.textContent = triage.priority;
    triageSentiment.textContent = triage.sentiment;
    triageEscalate.textContent = triage.should_escalate ? 'YES ⚠️' : 'NO';
    triageEscalate.style.color = triage.should_escalate ? 'var(--danger-color)' : 'var(--success-color)';
    triageReason.textContent = triage.reason_summary;
    
    // Update Trace
    traceIdEl.textContent = triage.run_id;
    loadTraceLog(triage.run_id);
  } catch (err) {
    alert(`Triage failed: ${err.message}`);
  } finally {
    btnTriage.disabled = false;
    btnTriage.textContent = 'Triage with AI';
  }
}

// 4. AI Draft response generation
async function generateDraft() {
  if (!activeTicketId) return;
  
  btnDraft.disabled = true;
  btnDraft.textContent = 'Generating...';
  
  try {
    const draft = await apiRequest(`/api/tickets/${activeTicketId}/draft`, { method: 'POST' });
    
    draftCard.style.display = 'block';
    draftReplyBody.textContent = draft.body;
    
    // Render citations
    citationsContainer.innerHTML = '';
    if (draft.citations && draft.citations.length > 0) {
      draft.citations.forEach(cit => {
        const span = document.createElement('span');
        span.className = 'citation-tag';
        span.textContent = cit;
        span.addEventListener('click', () => viewPolicyDocument(cit));
        citationsContainer.appendChild(span);
      });
    } else {
      citationsContainer.innerHTML = '<span style="color: var(--text-muted); font-size: 13px;">None</span>';
    }
    
    // Guardrail Status
    guardrailAlert.className = `guardrail-alert ${draft.guardrail.status === 'blocked' ? 'guardrail-blocked' : 'guardrail-passed'}`;
    if (draft.guardrail.status === 'blocked') {
      guardrailStatusText.innerHTML = `⚠️ <strong>Safety Guardrail Blocked:</strong> ${draft.guardrail.reason}`;
    } else {
      guardrailStatusText.innerHTML = `🛡️ <strong>Safety Guardrail Passed:</strong> Inputs and documents validated.`;
    }
    
    // Action Recommendations
    if (draft.recommended_actions && draft.recommended_actions.length > 0) {
      // Pick first action
      const action = draft.recommended_actions[0];
      
      // Auto-submit action proposal to backend to obtain action ID
      const actRequest = await apiRequest(`/api/tickets/${activeTicketId}/actions`, {
        method: 'POST',
        body: JSON.stringify({
          tool_name: action.tool_name,
          payload: action.payload,
          idempotency_key: action.payload.idempotency_key
        })
      });
      
      activeAction = actRequest;
      renderActionPanel(actRequest);
    } else {
      actionPanel.style.display = 'none';
      activeAction = null;
    }
    
    // Update Trace
    traceIdEl.textContent = draft.run_id;
    loadTraceLog(draft.run_id);
    
  } catch (err) {
    alert(`Draft generation failed: ${err.message}`);
  } finally {
    btnDraft.disabled = false;
    btnDraft.textContent = 'Generate Cited Draft';
  }
}

// 5. Render action details panel
function renderActionPanel(action) {
  actionPanel.style.display = 'block';
  actionToolName.textContent = action.tool_name;
  actionStatusBadge.textContent = action.status.toUpperCase();
  
  // Colors for action status
  if (action.status === 'approval_required') {
    actionStatusBadge.className = 'badge badge-priority-high';
  } else if (action.status === 'executed') {
    actionStatusBadge.className = 'badge badge-priority-low';
  } else {
    actionStatusBadge.className = 'badge badge-category';
  }
  
  actionReason.textContent = action.requires_human_approval ? 
    "⚠️ This action is sensitive and requires human review." : 
    "✅ This action is low-risk and was executed automatically.";
    
  actionPayloadPreview.innerHTML = `<strong>Payload:</strong><br>${JSON.stringify(JSON.parse(action.payload_json), null, 2)}`;
  
  updateActionPanelButtons();
}

// Enable/Disable approval controls depending on user role
function updateActionPanelButtons() {
  if (!activeAction) return;
  
  const requiresApproval = activeAction.status === 'approval_required';
  
  if (requiresApproval) {
    btnActionApprove.disabled = false;
    btnActionReject.disabled = false;
    
    // Visually show if they have the power to approve
    if (activeRole === 'support_agent') {
      btnActionApprove.title = 'Requires Manager or Admin role to approve';
      btnActionReject.title = 'Requires Manager or Admin role to reject';
    } else {
      btnActionApprove.title = '';
      btnActionReject.title = '';
    }
  } else {
    btnActionApprove.disabled = true;
    btnActionReject.disabled = true;
  }
}

// 6. Approve or Reject Recommended Action
async function handleActionApproval(approve) {
  if (!activeAction) return;
  
  const endpoint = `/api/actions/${activeAction.action_id}/${approve ? 'approve' : 'reject'}?role=${activeRole}`;
  
  try {
    const updatedAction = await apiRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify({ reason: `Action handled by ${activeRole} via dashboard.` })
    });
    
    activeAction = updatedAction;
    renderActionPanel(updatedAction);
    
    actionAgentMessage.style.display = 'block';
    actionAgentMessage.style.color = approve ? 'var(--success-color)' : 'var(--danger-color)';
    actionAgentMessage.textContent = approve ? 'Action executed successfully!' : 'Action rejected by manager.';
    
  } catch (err) {
    alert(`Action verification failed: ${err.message}`);
  }
}

// 7. Load trace log from database
async function loadTraceLog(runId) {
  try {
    const trace = await apiRequest(`/api/traces/${runId}`);
    traceLogContent.innerHTML = `
<strong>RUN TYPE:</strong> ${trace.run_type.toUpperCase()}
<strong>STATUS:</strong> ${trace.status.toUpperCase()}
<strong>RETRIEVED DOCS:</strong> ${JSON.stringify(JSON.parse(trace.retrieved_doc_ids_json))}
<strong>TOOL CALLS:</strong> ${JSON.stringify(JSON.parse(trace.tool_calls_json))}
<strong>GUARDRAILS STATUS:</strong> ${JSON.stringify(JSON.parse(trace.guardrail_results_json))}
<strong>TIMESTAMP:</strong> ${trace.created_at}
    `;
  } catch (err) {
    traceLogContent.textContent = `Error loading trace: ${err.message}`;
  }
}

// 8. View full policy document contents in modal overlay
async function viewPolicyDocument(docId) {
  try {
    const data = await apiRequest(`/api/knowledge/search?q=${docId}`);
    const doc = data.results.find(d => d.doc_id === docId) || data.results[0];
    
    if (doc) {
      policyModalTitle.textContent = `${doc.title} (${doc.doc_id})`;
      policyModalContent.textContent = doc.content;
      policyModal.style.display = 'flex';
    } else {
      alert(`Policy document ${docId} not found.`);
    }
  } catch (err) {
    alert(`Failed to retrieve policy: ${err.message}`);
  }
}

// 9. Load evaluation results dashboard
async function loadEvalResults() {
  try {
    const results = await apiRequest('/api/evals/results');
    
    if (results.length === 0) {
      resetEvalDashboard();
      return;
    }
    
    const latest = results[0];
    
    // Set Summary Metric Cards
    evalMetricTotal.textContent = latest.total_cases;
    
    const metrics = JSON.parse(latest.metrics_json);
    evalMetricCategory.textContent = `${(metrics.triage_category_accuracy * 100).toFixed(0)}%`;
    evalMetricPriority.textContent = `${(metrics.triage_priority_accuracy * 100).toFixed(0)}%`;
    evalMetricCitation.textContent = `${(metrics.citation_coverage * 100).toFixed(0)}%`;
    evalMetricSafety.textContent = `${(metrics.unsafe_action_block_rate * 100).toFixed(0)}%`;
    
    // Set results rows
    evalResultsTbody.innerHTML = '';
    const cases = JSON.parse(latest.case_results_json);
    
    cases.forEach(c => {
      const tr = document.createElement('tr');
      
      const categoryMatch = c.predicted_category === c.expected_category;
      const priorityMatch = c.predicted_priority === c.expected_priority;
      const citationsMatch = c.expected_citations.every(cid => c.citations.includes(cid));
      
      const containsDisallowed = c.disallowed_actions.some(act => c.recommended_actions.includes(act));
      const safetyMatch = !containsDisallowed;
      
      const escalationMatch = c.should_escalate == c.expected_escalation;
      
      tr.innerHTML = `
        <td style="font-family: monospace; font-weight: 600;">${c.case_id}</td>
        <td style="font-family: monospace;">${c.ticket_id}</td>
        <td>
          <span class="badge ${categoryMatch ? 'badge-priority-low' : 'badge-priority-urgent'}">Cat: ${categoryMatch ? 'OK' : 'ERR'}</span>
          <span class="badge ${priorityMatch ? 'badge-priority-low' : 'badge-priority-urgent'}">Prio: ${priorityMatch ? 'OK' : 'ERR'}</span>
        </td>
        <td>
          <span class="badge ${citationsMatch ? 'badge-priority-low' : 'badge-priority-urgent'}">${citationsMatch ? 'PASS' : 'FAIL'}</span>
        </td>
        <td>
          <span class="badge ${safetyMatch ? 'badge-priority-low' : 'badge-priority-urgent'}">${safetyMatch ? 'SECURE' : 'UNSAFE'}</span>
        </td>
        <td>
          <span class="badge ${escalationMatch ? 'badge-priority-low' : 'badge-priority-urgent'}">${escalationMatch ? 'OK' : 'ERR'}</span>
        </td>
        <td>
          <span class="${c.passed ? 'pass-badge' : 'fail-badge'}">${c.passed ? 'PASSED' : 'FAILED'}</span>
        </td>
      `;
      evalResultsTbody.appendChild(tr);
    });
    
  } catch (err) {
    alert(`Failed to load evaluation logs: ${err.message}`);
  }
}

// Reset eval cards
function resetEvalDashboard() {
  evalMetricTotal.textContent = '-';
  evalMetricCategory.textContent = '-';
  evalMetricPriority.textContent = '-';
  evalMetricCitation.textContent = '-';
  evalMetricSafety.textContent = '-';
  evalResultsTbody.innerHTML = `
    <tr>
      <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 40px 0;">
        No evaluations found. Click "Run Evals Suite" to execute.
      </td>
    </tr>
  `;
}

// 10. Start evaluation background suite execution
async function triggerEvalSuite() {
  btnRunEval.disabled = true;
  btnRunEval.textContent = 'Running...';
  
  try {
    const res = await apiRequest('/api/evals/run', { method: 'POST' });
    
    // Start polling for completed evaluations
    if (evalPollingInterval) clearInterval(evalPollingInterval);
    
    let iterations = 0;
    evalPollingInterval = setInterval(async () => {
      iterations++;
      try {
        const results = await apiRequest('/api/evals/results');
        if (results.length > 0) {
          // Compare completed run details
          clearInterval(evalPollingInterval);
          loadEvalResults();
          btnRunEval.disabled = false;
          btnRunEval.textContent = 'Run Evals Suite';
        }
      } catch (e) {
        clearInterval(evalPollingInterval);
        btnRunEval.disabled = false;
        btnRunEval.textContent = 'Run Evals Suite';
      }
      
      // Safety limit polling
      if (iterations > 10) {
        clearInterval(evalPollingInterval);
        btnRunEval.disabled = false;
        btnRunEval.textContent = 'Run Evals Suite';
      }
    }, 1500);
    
  } catch (err) {
    alert(`Failed to trigger evaluation run: ${err.message}`);
    btnRunEval.disabled = false;
    btnRunEval.textContent = 'Run Evals Suite';
  }
}

// Initialize load
loadTickets();
