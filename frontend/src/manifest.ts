export const manifest = {
  workflow_id: "ftg_revamped_flow_v1",
  workflow_name: "FTG - Dimension & Weight Capture",
  steps: [
    {
      step_id: 1,
      screen: "packaging_options",
      screenshot: "/screens/ftg_11.png",
      title: "Choose Packaging Type",
      instruction: "Tap 'Ships In Own Box' to select packaging",
      tip: "SIOB means the product ships in its original box without repackaging",
      expected_action: "TAP",
      on_wrong_action: "That's not right. Please tap 'Ships In Own Box'.",
      tap_target: { x: 3, y: 35, width: 94, height: 12 },
    },
    {
      step_id: 2,
      screen: "packaging_options",
      screenshot: "/screens/ftg_11.png",
      title: "Proceed to Next Step",
      instruction: "Tap 'Next' to continue",
      tip: null,
      expected_action: "TAP",
      on_wrong_action: "Tap the Next button at the bottom.",
      tap_target: { x: 4, y: 90, width: 92, height: 6 },
    },
    {
      step_id: 3,
      screen: "product_identifiers",
      screenshot: "/screens/ftg_06.png",
      title: "Select Product Category",
      instruction: "Tap the dropdown to select a category",
      tip: "Product category is mandatory when SDP config is enabled for your FC",
      expected_action: "TAP",
      on_wrong_action: "Please tap the Product Category dropdown.",
      tap_target: { x: 4, y: 35, width: 92, height: 6 },
    },
    {
      step_id: 4,
      screen: "product_identifiers",
      screenshot: "/screens/ftg_06.png",
      title: "Continue to Dimensions",
      instruction: "Tap 'Next' to proceed",
      tip: "Scannable ID and Image URL are optional fields",
      expected_action: "TAP",
      on_wrong_action: "Tap the Next button at the bottom.",
      tap_target: { x: 4, y: 90, width: 92, height: 6 },
    },
  ],
  quiz_breaks: [
    {
      after_step: 2,
      questions: [
        {
          question: "What does SIOCB stand for?",
          options: [
            "Ships In Own Box",
            "Ships In Own Case Box",
            "Ships In Original Container Box",
            "Standard Item Own Case Box",
          ],
          correct: 1,
        },
      ],
    },
  ],
};

// Add more steps after screenshots are available
// Steps 5-12 cover the Dimension & Weight screen
