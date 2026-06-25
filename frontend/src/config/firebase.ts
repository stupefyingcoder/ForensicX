import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAPVMiRw3HfXrztPiONMuNFsnkLn_SqMVA",
  authDomain: "forensicx.firebaseapp.com",
  projectId: "forensicx",
  storageBucket: "forensicx.firebasestorage.app",
  messagingSenderId: "175382910503",
  appId: "1:175382910503:web:b5f304ae4561fd65076002",
};

const app = initializeApp(firebaseConfig);

export const firebaseAuth = getAuth(app);
