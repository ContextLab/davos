# ADD DOCSTRING


class DotDict(dict):
    # ADD DOCSTRING
    # simple helper that allows a dict to be accessed like a JS object
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, d):
        # ADD DOCSTRING
        for k, v in d.items():
            if isinstance(v, dict):
                v = DotDict(v)
            self[k] = v


JS_FUNCTIONS = DotDict({
    'jupyter': {
        'restartRunCellsAbove': """\
            const restartRunCellsAbove = function() {
                const outputArea = this,
                    notebook = Jupyter.notebook,
                    // first cell currently selected, if multiple
                    anchorCellIndex = notebook.get_anchor_index(),
                    // most recently selected cell, if multiple
                    selectedCellIndex = notebook.get_selected_index(),
                    runningCell = outputArea.element.parents('.cell'),
                    allCells = notebook.get_cell_elements(),
                    runningCellIndex = allCells.index(runningCell);

                const queueCellsAndResetSelection = function() {
                    notebook.execute_cell_range(0, runningCellIndex + 1);
                    notebook.select(anchorCellIndex);
                    if (selectedCellIndex !== anchorCellIndex) {
                        // select multiple cells without moving anchor
                        notebook.select(selectedCellIndex, false);
                    }
                }

                notebook.kernel.restart(queueCellsAndResetSelection);
            }.bind(this)
        """,
        # TODO: don't forget to remove event listeners from all buttons
        'displayButtonPrompt': """\
            /**
             * Display one or more buttons for user selection and block until one is clicked
             * @param {...Object} buttonArgs - Objects containing data for each button/option 
             *     to be displayed.
             * @param {string} [buttonArgs.text="Button X"] - Text label for the given button. 
             *     Defaults to "Button X", where "X" is the button number (index + 1).
             * @param {function} [buttonArgs.onClick] - Callback run when the given button is 
             *     clicked. Defaults to `console.log('Button X clicked');`, where X has the 
             *     same meaning as above.
             * @param {string} [buttonArgs.id] - Optional id for the given button element.
             * @param {*} [buttonArgs.result] - 
             */
            const displayButtonPrompt = function(...buttonArgs) {
                const outputArea = this,
                    outputDisplayArea = element[0],
                    callbackPromise = new Promise((resolve) => resolutionFunc = resolve );
                let onClick, clickedButtonCallback, resolutionFunc
                
                buttonArgs.forEach(function (buttonObj, ix) {
                    let buttonElement = document.createElement('BUTTON');
                    buttonElement.style.marginLeft = '1rem';
                    buttonElement.classList.add('davos', 'prompt-button');
                    if (typeof buttonObj.id !== 'undefined') {
                        buttonElement.id = buttonObj.id;
                    }
                    if (typeof buttonObj.text === 'undefined') {
                        buttonElement.textContent = `Button ${ix + 1}`;
                    } else {
                        buttonElement.textContent = buttonObj.text;
                    }
                    onClick = (typeof buttonObj.onClick === 'undefined') ? () => {} : buttonObj.onClick;
                    buttonElement.addEventListener('click', () => {
                        clickedButtonCallback = onClick;
                        resolutionFunc();
                    })
                    
                    if (typeof buttonObj.onClick === 'undefined') {
                        onClick = () => console.log(`Button ${ix + 1} clicked`);
                    } else {
                        onClick = buttonObj.onClick
                    }
                    
                    
                });
                
            }.bind(this)
        """
    }
})
