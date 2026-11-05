// Original course introductions and links to external educational resources.
// Keep public guides separate from subscription-protected learning access.
const COURSE_GUIDES = {
  blue: {
    introduction: "Safer habits start with understanding the risks.",
    why: "Passwords, messages, and everyday websites all involve decisions about trust. Learning digital safety helps you recognise common threats, protect personal information, and respond more carefully when something looks wrong.",
    application: "Use these skills when securing an account, spotting a suspicious message, or deciding what information to share online.",
    skills: ["Recognise common phishing and social engineering signals", "Use stronger account security and safer password habits", "Explain why privacy and access permissions matter"],
    examples: ["Check whether a sign-in request is legitimate before entering a password.", "Choose what personal information a learning platform should collect.", "Understand why a learner cannot use educator or administrator functions."],
    video: {
      title: "Cybersecurity for Beginners | Google Cybersecurity Certificate",
      level: "Topic overview",
      creator: "Grow with Google",
      url: "https://www.youtube.com/watch?v=_DVVNOGYtmU",
      thumbnail: "/thumbnails/_DVVNOGYtmU.jpg",
      topic: "An introduction to cybersecurity, risks, and security controls.",
      source: "https://www.youtube.com/watch?v=_DVVNOGYtmU"
    },
    relatedVideos: [
      {
        title: "Cybersecurity: Crash Course Computer Science #31",
        creator: "CrashCourse · PBS Digital Studios",
        url: "https://www.youtube.com/watch?v=bPVaOlJ6ln0",
        thumbnail: "/thumbnails/bPVaOlJ6ln0.jpg",
        topic: "Understand what security protects and how passwords, access privileges, and two-factor authentication help protect information.",
        source: "https://thecrashcourse.com/courses/cybersecurity-crash-course-computer-science-31/",
        level: "Start here"
      },
      {
        title: "How to Choose a Password - Computerphile",
        creator: "Computerphile · Dr Mike Pound",
        url: "https://www.youtube.com/watch?v=3NjQ9b3pgIg",
        thumbnail: "/thumbnails/3NjQ9b3pgIg.jpg",
        topic: "Explore why password length and predictability matter when choosing a password for a learner account.",
        source: "https://www.youtube.com/watch?v=3NjQ9b3pgIg",
        level: "Account security"
      },
      {
        title: "How Password Managers Work - Computerphile",
        creator: "Computerphile · Dr Mike Pound",
        url: "https://www.youtube.com/watch?v=w68BBPDAWr8",
        thumbnail: "/thumbnails/w68BBPDAWr8.jpg",
        topic: "Learn how password managers support using a different strong password for each account.",
        source: "https://www.youtube.com/watch?v=w68BBPDAWr8",
        level: "Everyday practice"
      }
    ]
  },
  violet: {
    introduction: "Understand the data behind the websites you use.",
    why: "A learning platform has to connect users, subscriptions, courses, and progress without mixing up their records. SQL helps you organise those relationships, retrieve accurate information, and turn stored data into useful reports.",
    application: "Use SQL to answer questions such as which learners have an active subscription, which courses they can open, and how much progress they have made.",
    skills: ["Explain tables, primary keys, and relationships", "Read and write basic SQL queries", "Join related records and filter results for a report"],
    examples: ["Find learners whose subscription is still active.", "Join courses to the plans that include them.", "Build a report of completed learning items without changing another user's data."],
    video: {
      title: "SQL Tutorial - Full Database Course for Beginners",
      level: "Full beginner course",
      creator: "freeCodeCamp.org · Mike Dane",
      url: "https://www.youtube.com/watch?v=HXV3zeQKqGY",
      thumbnail: "/thumbnails/HXV3zeQKqGY.jpg",
      topic: "A beginner course covering databases, SQL queries, keys, and joins.",
      source: "https://www.freecodecamp.org/news/sql-and-databases-full-course/"
    },
    relatedVideos: [
      {
        title: "Database Design Course - Learn how to design and plan a database for beginners",
        creator: "freeCodeCamp.org · Caleb Curry",
        url: "https://www.youtube.com/watch?v=ztHopE5Wnpc",
        thumbnail: "/thumbnails/ztHopE5Wnpc.jpg",
        topic: "Learn how to plan a database, connect related tables, and make design decisions before building your application.",
        source: "https://www.freecodecamp.org/news/database-design-course-for-beginners",
        level: "Database foundations"
      },
      {
        title: "Relational Database Design - Full Course",
        creator: "freeCodeCamp.org",
        url: "https://www.youtube.com/watch?v=26ls5lNiijk",
        thumbnail: "/thumbnails/26ls5lNiijk.jpg",
        topic: "Explore relationships, keys, normalisation, and constraints to organise users, subscriptions, and progress records more clearly.",
        source: "https://www.freecodecamp.org/news/learn-relational-database-design",
        level: "Further study"
      },
      {
        title: "MySQL Database - Full Course",
        creator: "freeCodeCamp.org · Bharath Ram Manoharan",
        url: "https://www.youtube.com/watch?v=ER8oKX5myE0",
        thumbnail: "/thumbnails/ER8oKX5myE0.jpg",
        topic: "Practise creating tables, working with records, and joining related data. Continue into indexes and transactions when you are ready.",
        source: "https://www.freecodecamp.org/news/learn-to-use-the-mysql-database",
        level: "SQL practice"
      }
    ]
  },
  teal: {
    introduction: "Build websites that protect the people using them.",
    why: "A website must check who a user is, which actions they are allowed to perform, and whether submitted data is valid. Secure application design helps you make those decisions on the server and reduce opportunities for unauthorised access.",
    application: "Apply these ideas when building login, protecting a course, processing form input, or deciding who can publish educational content.",
    skills: ["Distinguish authentication from authorisation", "Understand server-side access and input checks", "Explain how audit records support investigation"],
    examples: ["Reject a learner request to approve educator content.", "Check a subscription before returning a protected learning item.", "Treat user text as data so it cannot become executable page content."],
    video: {
      title: "OWASP API Security Top 10 Course - Secure Your Web Apps",
      level: "API security",
      creator: "freeCodeCamp.org · APIsec University",
      url: "https://www.youtube.com/watch?v=YYe0FdfdgDU",
      thumbnail: "/thumbnails/YYe0FdfdgDU.jpg",
      topic: "Corey Ball introduces the OWASP API Security Top 10, 2023 edition. Best after basic web development.",
      source: "https://www.freecodecamp.org/news/owasp-api-security-top-10-secure-your-apis"
    },
    relatedVideos: [
      {
        title: "Learn HTML & CSS - Full Course for Beginners",
        creator: "freeCodeCamp.org",
        url: "https://www.youtube.com/watch?v=a_iQb1lnAEQ",
        thumbnail: "/thumbnails/a_iQb1lnAEQ.jpg",
        topic: "Learn webpage structure and styling before moving on to secure application design. Build your understanding of forms, layouts, and page elements.",
        source: "https://www.youtube.com/watch?v=a_iQb1lnAEQ",
        level: "Frontend foundations"
      },
      {
        title: "JavaScript Programming - Full Course",
        creator: "freeCodeCamp.org · Per Borgen",
        url: "https://www.youtube.com/watch?v=jS4aFq5-91M",
        thumbnail: "/thumbnails/jS4aFq5-91M.jpg",
        topic: "Learn variables, functions, DOM updates, and user interaction through small projects. Apply these foundations to interactive website features.",
        source: "https://www.freecodecamp.org/news/full-javascript-course-for-beginners",
        level: "Frontend practice"
      },
      {
        title: "User Authentication in Web Apps (Passport.js, Node, Express)",
        creator: "freeCodeCamp.org · Zach Gollwitzer",
        url: "https://www.youtube.com/watch?v=F-sFp_AvHc8",
        thumbnail: "/thumbnails/F-sFp_AvHc8.jpg",
        topic: "Study login forms, cookies, sessions, and JWT authentication with Node and Express examples. Explore how applications keep track of signed-in users.",
        source: "https://www.freecodecamp.org/news/learn-to-implement-user-authentication-in-node-apps-using-passport-js",
        level: "Authentication practice"
      }
    ]
  }
};

function getCourseGuide(item) {
  const topic = (item.title + " " + item.category).toLowerCase();
  if (/sql|database|relational/.test(topic)) return COURSE_GUIDES.violet;
  if (/web|application|development|api/.test(topic)) return COURSE_GUIDES.teal;
  if (/cyber|security|privacy|digital safety/.test(topic)) return COURSE_GUIDES.blue;
  return {
    introduction: "Explore the purpose and learning goals of this resource.",
    why: item.description,
    application: "Use the resource description to connect this topic to a task or problem you want to understand. Identify a practical example and check your understanding as you learn.",
    skills: ["Explain the main ideas in your own words", "Connect the topic to a practical example", "Identify questions to explore with your educator"],
    examples: ["Choose a realistic problem related to this topic.", "Note which ideas help explain or solve that problem.", "Review your understanding and record your learning progress."],
    video: {
      title: "Find videos about " + item.title,
      creator: "YouTube topic search",
      url: "https://www.youtube.com/results?search_query=" + encodeURIComponent(item.title + " beginner tutorial"),
      topic: "No specific video has been curated for this topic yet. This link opens YouTube search results so you can compare educational videos and their creators.",
      source: null
    }
  };
}
