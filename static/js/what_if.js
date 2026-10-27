/**
 * What-If Simulator for RiskWise Prediction Results.
 * Debounced slider and number input updates for all 10 application parameters.
 */
document.addEventListener("DOMContentLoaded", function () {
    const card = document.getElementById("what-if-card");
    if (!card) return;

    const apiUrl = card.dataset.apiUrl;
    const limitsDataElem = document.getElementById("whatif-limits-data");
    const limitsData = limitsDataElem ? JSON.parse(limitsDataElem.textContent) : {};

    const scoreElem = document.getElementById("whatif-score");
    const riskPill = document.getElementById("whatif-risk-pill");
    const probElem = document.getElementById("whatif-prob");
    const deltaElem = document.getElementById("whatif-delta");
    const resetBtn = document.getElementById("whatif-reset-btn");
    const errorElem = document.getElementById("whatif-error");
    const changesBadge = document.getElementById("whatif-changes-badge");
    const scoreBox = document.getElementById("whatif-score-box");
    const spinner = document.getElementById("whatif-loading-spinner");

    const numericFields = [
        "person_income",
        "loan_amnt",
        "loan_int_rate",
        "person_age",
        "person_emp_length",
        "cb_person_cred_hist_length"
    ];

    const selectFields = [
        "person_home_ownership",
        "loan_intent",
        "loan_grade",
        "cb_person_default_on_file"
    ];

    function formatAmount(val) {
        return "$" + Math.round(Number(val)).toLocaleString("en-US");
    }

    function formatValue(field, val) {
        if (field === "person_income" || field === "loan_amnt") {
            return formatAmount(val);
        }
        if (field === "loan_int_rate") {
            return parseFloat(val).toFixed(1) + "%";
        }
        if (field === "person_age" || field === "person_emp_length" || field === "cb_person_cred_hist_length") {
            return Math.round(val) + " yrs";
        }
        return val;
    }

    function updateSliderLabels(field, slider) {
        const group = document.querySelector(`.whatif-field-group[data-field="${field}"]`);
        if (!group) return;
        const minLabel = group.querySelector(".whatif-min-label");
        const maxLabel = group.querySelector(".whatif-max-label");
        if (minLabel) minLabel.textContent = formatValue(field, slider.min);
        if (maxLabel) maxLabel.textContent = formatValue(field, slider.max);
    }

    function checkChanges() {
        let count = 0;

        // Check numeric fields
        numericFields.forEach((field) => {
            const numInput = document.querySelector(`.whatif-num-input[data-field="${field}"]`);
            const slider = document.querySelector(`.whatif-range[data-field="${field}"]`);
            if (!numInput) return;

            const current = parseFloat(numInput.value);
            const initial = parseFloat(numInput.dataset.initial);
            const isChanged = !isNaN(current) && Math.abs(current - initial) > 0.001;

            if (isChanged) {
                count++;
                numInput.classList.add("whatif-field-changed");
                if (slider) slider.classList.add("whatif-field-changed");
            } else {
                numInput.classList.remove("whatif-field-changed");
                if (slider) slider.classList.remove("whatif-field-changed");
            }
        });

        // Check select fields
        selectFields.forEach((field) => {
            const select = document.querySelector(`.whatif-select[data-field="${field}"]`);
            if (!select) return;

            const isChanged = select.value !== select.dataset.initial;
            if (isChanged) {
                count++;
                select.classList.add("whatif-field-changed");
            } else {
                select.classList.remove("whatif-field-changed");
            }
        });

        if (changesBadge) {
            changesBadge.textContent = `${count} change${count === 1 ? "" : "s"} vs saved result`;
        }
        return count;
    }

    function showInlineError(field, message) {
        const errElem = document.getElementById(`whatif-err-${field}`);
        const input = document.querySelector(`[data-field="${field}"]`);
        if (errElem) {
            errElem.textContent = message;
            errElem.classList.remove("d-none");
        }
        if (input) {
            input.classList.add("is-invalid");
        }
    }

    function clearInlineError(field) {
        const errElem = document.getElementById(`whatif-err-${field}`);
        const input = document.querySelector(`[data-field="${field}"]`);
        if (errElem) {
            errElem.textContent = "";
            errElem.classList.add("d-none");
        }
        if (input) {
            input.classList.remove("is-invalid");
        }
    }

    function hasValidationErrors() {
        let hasError = false;
        numericFields.forEach((field) => {
            const numInput = document.querySelector(`.whatif-num-input[data-field="${field}"]`);
            if (!numInput) return;
            const val = parseFloat(numInput.value);
            const limits = limitsData[field] || {};
            const min = limits.min !== undefined ? limits.min : -Infinity;
            const max = limits.max !== undefined ? limits.max : Infinity;

            if (isNaN(val) || val < min || val > max) {
                hasError = true;
                showInlineError(field, `Must be between ${formatValue(field, min)} and ${formatValue(field, max)}.`);
            } else {
                clearInlineError(field);
            }
        });
        return hasError;
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

        if (hasValidationErrors()) {
            return;
        }

        const params = new URLSearchParams();

        numericFields.forEach((field) => {
            const input = document.querySelector(`.whatif-num-input[data-field="${field}"]`);
            if (input && input.value !== "") {
                params.set(field, input.value);
            }
        });

        selectFields.forEach((field) => {
            const select = document.querySelector(`.whatif-select[data-field="${field}"]`);
            if (select && select.value !== "") {
                params.set(field, select.value);
            }
        });

        // Show subtle loading state
        if (scoreBox) scoreBox.classList.add("opacity-50");
        if (spinner) spinner.classList.remove("d-none");

        try {
            const response = await fetch(`${apiUrl}?${params.toString()}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });

            if (response.status === 429) {
                if (errorElem) {
                    errorElem.textContent = "Rate limit reached (120/min). Please wait a moment.";
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
                if (errData.field) {
                    showInlineError(errData.field, errData.error);
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
        } finally {
            if (scoreBox) scoreBox.classList.remove("opacity-50");
            if (spinner) spinner.classList.add("d-none");
        }
    }

    const debouncedSimulate = debounce(runSimulation, 250);

    // Number inputs & Sliders synchronization
    numericFields.forEach((field) => {
        const numInput = document.querySelector(`.whatif-num-input[data-field="${field}"]`);
        const slider = document.querySelector(`.whatif-range[data-field="${field}"]`);

        if (numInput && slider) {
            // Typing in number input
            numInput.addEventListener("input", function () {
                const val = parseFloat(numInput.value);
                const limits = limitsData[field] || {};
                const min = limits.min !== undefined ? limits.min : -Infinity;
                const max = limits.max !== undefined ? limits.max : Infinity;

                if (!isNaN(val) && val >= min && val <= max) {
                    clearInlineError(field);
                    // Extend slider range if user typed outside current slider range
                    let sMin = parseFloat(slider.min);
                    let sMax = parseFloat(slider.max);
                    if (val < sMin) {
                        slider.min = val;
                        updateSliderLabels(field, slider);
                    }
                    if (val > sMax) {
                        slider.max = val;
                        updateSliderLabels(field, slider);
                    }
                    slider.value = val;
                    checkChanges();
                    debouncedSimulate();
                } else if (isNaN(val) || val < min || val > max) {
                    showInlineError(field, `Must be between ${formatValue(field, min)} and ${formatValue(field, max)}.`);
                    // Do not call API on invalid range
                }
            });

            // Moving slider
            slider.addEventListener("input", function () {
                numInput.value = slider.value;
                clearInlineError(field);
                checkChanges();
                debouncedSimulate();
            });
        }
    });

    // Select inputs
    selectFields.forEach((field) => {
        const select = document.querySelector(`.whatif-select[data-field="${field}"]`);
        if (select) {
            select.addEventListener("change", function () {
                clearInlineError(field);
                checkChanges();
                debouncedSimulate();
            });
        }
    });

    // Reset button
    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            // Reset numeric fields
            numericFields.forEach((field) => {
                const numInput = document.querySelector(`.whatif-num-input[data-field="${field}"]`);
                const slider = document.querySelector(`.whatif-range[data-field="${field}"]`);
                if (numInput && numInput.dataset.initial !== undefined) {
                    numInput.value = numInput.dataset.initial;
                }
                if (slider) {
                    if (slider.dataset.initialMin !== undefined) slider.min = slider.dataset.initialMin;
                    if (slider.dataset.initialMax !== undefined) slider.max = slider.dataset.initialMax;
                    if (slider.dataset.initialStep !== undefined) slider.step = slider.dataset.initialStep;
                    if (slider.dataset.initial !== undefined) slider.value = slider.dataset.initial;
                    updateSliderLabels(field, slider);
                }
                clearInlineError(field);
            });

            // Reset select fields
            selectFields.forEach((field) => {
                const select = document.querySelector(`.whatif-select[data-field="${field}"]`);
                if (select && select.dataset.initial !== undefined) {
                    select.value = select.dataset.initial;
                }
                clearInlineError(field);
            });

            if (errorElem) errorElem.classList.add("d-none");

            // Reset saved score and pill
            if (scoreElem && scoreElem.dataset.saved) scoreElem.textContent = scoreElem.dataset.saved;
            if (riskPill && riskPill.dataset.savedLevel) {
                riskPill.className = "risk-badge";
                riskPill.classList.add(`risk-${riskPill.dataset.savedLevel}`);
                riskPill.textContent = riskPill.dataset.savedLabel;
            }
            if (probElem && probElem.dataset.saved) probElem.textContent = probElem.dataset.saved;
            if (deltaElem) {
                deltaElem.textContent = "0 points vs your result";
                deltaElem.style.color = "#475569";
                deltaElem.style.backgroundColor = "#F1F5F9";
            }

            checkChanges();
        });
    }

    // Initial check
    checkChanges();
});
