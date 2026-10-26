/**
 * What-If Simulator for RiskWise Prediction Results.
 * Debounced slider updates to evaluate scenario changes in real-time.
 */
document.addEventListener("DOMContentLoaded", function () {
    const card = document.getElementById("what-if-card");
    if (!card) return;

    const apiUrl = card.dataset.apiUrl;
    const incomeInput = document.getElementById("whatif-income");
    const loanInput = document.getElementById("whatif-loan");
    const rateInput = document.getElementById("whatif-rate");
    const empInput = document.getElementById("whatif-emp");

    const incomeVal = document.getElementById("whatif-income-val");
    const loanVal = document.getElementById("whatif-loan-val");
    const rateVal = document.getElementById("whatif-rate-val");
    const empVal = document.getElementById("whatif-emp-val");

    const scoreElem = document.getElementById("whatif-score");
    const riskPill = document.getElementById("whatif-risk-pill");
    const probElem = document.getElementById("whatif-prob");
    const deltaElem = document.getElementById("whatif-delta");
    const resetBtn = document.getElementById("whatif-reset-btn");
    const errorElem = document.getElementById("whatif-error");

    function formatCurrency(val) {
        return "$" + Number(val).toLocaleString("en-US");
    }

    function updateLabels() {
        if (incomeVal && incomeInput) incomeVal.textContent = formatCurrency(incomeInput.value);
        if (loanVal && loanInput) loanVal.textContent = formatCurrency(loanInput.value);
        if (rateVal && rateInput) rateVal.textContent = parseFloat(rateInput.value).toFixed(1) + "%";
        if (empVal && empInput) empVal.textContent = parseFloat(empInput.value).toFixed(0) + " yrs";
    }

    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    async function runSimulation() {
        if (!apiUrl) return;

        const params = new URLSearchParams({
            person_income: incomeInput.value,
            loan_amnt: loanInput.value,
            loan_int_rate: rateInput.value,
            person_emp_length: empInput.value,
        });

        try {
            const response = await fetch(`${apiUrl}?${params.toString()}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });

            if (response.status === 429) {
                if (errorElem) {
                    errorElem.textContent = "Rate limit reached (60/min). Please wait a moment.";
                    errorElem.classList.remove("d-none");
                }
                return;
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                if (errorElem) {
                    errorElem.textContent = errData.error || "Simulation error. Please check your inputs.";
                    errorElem.classList.remove("d-none");
                }
                return;
            }

            const data = await response.json();
            if (errorElem) {
                errorElem.classList.add("d-none");
            }

            // Update score
            if (scoreElem) {
                scoreElem.textContent = data.score;
            }

            // Update risk pill
            if (riskPill) {
                riskPill.className = "risk-badge";
                const lvl = (data.risk_level || "").toLowerCase();
                riskPill.classList.add(`risk-${lvl}`);
                riskPill.textContent = data.risk_label || `${data.risk_level} Risk`;
            }

            // Update probability
            if (probElem) {
                probElem.textContent = `${data.probability_pct}%`;
            }

            // Update delta
            if (deltaElem) {
                const delta = data.delta_score;
                if (delta > 0) {
                    deltaElem.textContent = `+${delta} points vs your result`;
                    deltaElem.style.color = "#047857";
                    deltaElem.style.backgroundColor = "#D1FAE5";
                } else if (delta < 0) {
                    deltaElem.textContent = `${delta} points vs your result`;
                    deltaElem.style.color = "#B91C1C";
                    deltaElem.style.backgroundColor = "#FEE2E2";
                } else {
                    deltaElem.textContent = "0 points vs your result";
                    deltaElem.style.color = "#475569";
                    deltaElem.style.backgroundColor = "#F1F5F9";
                }
            }
        } catch (err) {
            if (errorElem) {
                errorElem.textContent = "Unable to connect to simulation service. Please try again.";
                errorElem.classList.remove("d-none");
            }
        }
    }

    const debouncedSimulate = debounce(runSimulation, 250);

    const inputs = [incomeInput, loanInput, rateInput, empInput];
    inputs.forEach((input) => {
        if (!input) return;
        input.addEventListener("input", function () {
            updateLabels();
            debouncedSimulate();
        });
    });

    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            inputs.forEach((input) => {
                if (input && input.dataset.initial !== undefined) {
                    input.value = input.dataset.initial;
                }
            });
            updateLabels();
            runSimulation();
        });
    }

    // Initial label refresh
    updateLabels();
});
