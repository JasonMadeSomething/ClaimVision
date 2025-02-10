import { Amplify } from "aws-amplify";
import awsExports from "./aws-exports";

console.log("Amplify Config:", awsExports);

Amplify.configure(awsExports as any);

export default Amplify;
